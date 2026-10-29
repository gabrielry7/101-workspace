"""Controlled financial effects, authority and compensation on SQLite/optional PG."""

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_payment_durability_m3 import factory as shared_factory
from test_payment_durability_m3 import request
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.errors import (
    InvalidTransitionError,
    PaymentError,
    ValidationError,
)
from world_model.restaurant_commerce.financial_auth import FinancialPrincipal
from world_model.restaurant_commerce.financial_providers import (
    PaymentObservation,
    RefundObservation,
)
from world_model.restaurant_commerce.models import (
    FinancialAudit,
    FinancialOperation,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    LoyaltyRefundDebt,
    Order,
    PaymentIntent,
    utcnow,
)
from world_model.restaurant_commerce.payments import SimulatedPaymentProvider
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture
def factory(tmp_path):
    yield from shared_factory.__wrapped__(tmp_path)


def principal(**overrides):
    return replace(
        FinancialPrincipal(
            "staff:alice",
            frozenset({BID}),
            frozenset({"finance.read", "finance.lookup", "finance.refund", "finance.resolve"}),
            utcnow() + timedelta(hours=1),
        ),
        **overrides,
    )


class Controlled(SimulatedPaymentProvider):
    controlled = True
    supports_idempotent_refund = True

    def __init__(self):
        self.payments, self.refunds = {}, {}
        self.effects, self.calls = 0, 0
        self.lose_refund = False
        self.lose_checkout = False
        self.unknown = False
        self.bad = None
        self.callback = None

    def create_checkout(self, **kw):
        result = super().create_checkout(**kw)
        self.payments[kw["order_id"]] = PaymentObservation(
            kw["order_id"],
            result.provider_reference,
            result.amount_minor,
            result.currency,
            "paid",
            "settlement:" + kw["order_id"],
        )
        if self.lose_checkout:
            raise TimeoutError("accepted checkout; reply lost")
        return replace(result, status="paid")

    def lookup_payment(self, **kw):
        if self.unknown:
            return None
        result = self.payments[kw["order_id"]]
        return replace(result, **self.bad) if self.bad else result

    def lookup_refund(self, **kw):
        return self.refunds.get(kw["idempotency_key"])

    def refund(self, **kw):
        self.calls += 1
        if self.callback:
            self.callback()
        key = kw["idempotency_key"]
        if key not in self.refunds:
            self.refunds[key] = RefundObservation(
                kw["order_id"],
                kw["provider_reference"],
                kw["amount_minor"],
                kw["currency"],
                "succeeded",
                "evidence:" + key,
                "ref:" + key,
            )
            self.effects += 1
        if self.lose_refund:
            raise TimeoutError("refund accepted; reply lost")
        return self.refunds[key]


def setup(factory, provider=None):
    provider = provider or Controlled()
    session = factory()
    service = RestaurantCommerceService(
        session,
        payment_providers={"simulated": provider},
        financial_providers={"simulated": provider},
    )
    order = service.create_order(BID, request(service))
    return session, service, provider, order


def refund(service, order, key="refund-click"):
    return service.request_financial_operation(
        BID, order.id, "refund", key, "Customer requested full refund", principal()
    )


def test_refund_lost_reply_recovers_original_intent_once(factory):
    session, svc, provider, order = setup(factory)
    provider.lose_refund = True
    result = refund(svc, order)
    assert result["state"] == "unknown"
    assert svc.order_out(order.id).payment_status == "paid"
    with pytest.raises(InvalidTransitionError):
        svc.transition_order(order.id, "accepted")
    session.close()
    with factory() as session:
        restarted = RestaurantCommerceService(session, financial_providers={"simulated": provider})
        result = restarted.process_financial_operation(result["id"])
        assert result["state"] == "succeeded"
        assert restarted.order_out(order.id).payment_status == "refunded"
        again = refund(restarted, order, "another-tab")
        assert again["id"] == result["id"]
        assert provider.effects == provider.calls == 1
        assert len(list(session.scalars(select(FinancialOperation)))) == 1
        audits = list(session.scalars(select(FinancialAudit)))
        assert {x.action for x in audits} == {
            "refund.requested",
            "refund.unknown",
            "refund.succeeded",
        }
        assert all(x.actor_id == "staff:alice" for x in audits)


def test_refund_concurrent_replay_returns_same_pending_intent(factory):
    session, svc, provider, order = setup(factory)
    seen = []

    def concurrent():
        with factory() as other:
            replay = RestaurantCommerceService(other, financial_providers={"simulated": provider})
            seen.append(refund(replay, order, "other-tab"))

    provider.callback = concurrent
    result = refund(svc, order)
    assert seen[0]["id"] == result["id"] and seen[0]["state"] == "processing"
    assert provider.effects == provider.calls == 1
    session.close()


def test_lookup_recovers_provider_payment_without_second_checkout(factory):
    provider = Controlled()
    provider.lose_checkout = True
    with factory() as session:
        svc = RestaurantCommerceService(
            session,
            payment_providers={"simulated": provider},
            financial_providers={"simulated": provider},
        )
        with pytest.raises(PaymentError):
            svc.create_order(BID, request(svc))
        order = session.scalar(select(Order))
        result = svc.request_financial_operation(
            BID, order.id, "lookup", "lookup-key", "Investigate lost response", principal()
        )
        assert result["state"] == "succeeded"
        assert svc.order_out(order.id).payment_status == "paid"
        assert session.scalar(select(PaymentIntent)).state == "ready"
        assert len(provider.payments) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"amount_minor": 1},
        {"amount_minor": True},
        {"currency": "USD"},
        {"order_id": "wrong"},
        {"provider_reference": "wrong"},
        {"status": "partial_refund"},
        {"evidence_id": "\ud800"},
        {"evidence_id": {"untrusted": "object"}},
        {"evidence_id": 123},
        {"evidence_id": None},
    ],
)
def test_wrong_provider_evidence_remains_review(factory, bad):
    session, svc, provider, order = setup(factory)
    provider.bad = bad
    result = svc.request_financial_operation(
        BID, order.id, "lookup", "lookup-key", "Verify mismatch", principal()
    )
    assert result["state"] == "review_required"
    assert svc.order_out(order.id).payment_status == "paid"
    assert svc.list_payment_reconciliation(BID)
    session.close()


def test_unknown_lookup_cannot_resolve_review(factory):
    session, svc, provider, order = setup(factory)
    provider.unknown = True
    result = svc.request_financial_operation(
        BID, order.id, "lookup", "lookup-key", "Missing provider evidence", principal()
    )
    row = svc.list_payment_reconciliation(BID)[0]
    with pytest.raises(ValidationError):
        svc.resolve_financial_review(BID, order.id, row["id"], result["id"], "Close", principal())
    assert row["status"] == "open"
    session.close()


def test_resolution_audited_and_later_contradiction_reopens(factory):
    session, svc, provider, order = setup(factory)
    result = refund(svc, order)
    row = svc.list_payment_reconciliation(BID)[0]
    assert (
        svc.resolve_financial_review(
            BID, order.id, row["id"], result["id"], "Provider confirmed full refund", principal()
        )["status"]
        == "resolved"
    )
    svc.resolve_financial_review(
        BID, order.id, row["id"], result["id"], "Retry same resolution", principal()
    )
    assert (
        len(
            list(
                session.scalars(
                    select(FinancialAudit).where(FinancialAudit.action == "reconciliation.resolved")
                )
            )
        )
        == 1
    )
    svc._reconciliation(session.get(Order, order.id), row["reason"], {"new": "contradiction"})
    session.commit()
    assert svc.list_payment_reconciliation(BID)[0]["status"] == "open"
    with pytest.raises(PaymentError):
        svc.resolve_financial_review(
            BID, order.id, row["id"], result["id"], "Reuse stale proof", principal()
        )
    session.close()


def test_refund_reverses_earned_points_once_with_explicit_debt(factory):
    session, svc, provider, order = setup(factory)
    row = session.get(Order, order.id)
    account = LoyaltyAccount(
        business_id=BID, customer_id=row.customer_id, available_points=2, lifetime_earned_points=10
    )
    session.add(account)
    session.flush()
    session.add(
        LoyaltyLedgerEntry(
            account_id=account.id,
            order_id=row.id,
            delta_points=10,
            reason="order.completed",
            idempotency_key="order-complete:" + row.id,
        )
    )
    session.commit()
    result = refund(svc, order)
    session.refresh(account)
    assert account.available_points == 0 and account.lifetime_earned_points == 0
    debt = session.scalar(select(LoyaltyRefundDebt))
    assert debt.remaining_points == 8
    refund(svc, order, "new-click")
    assert len(list(session.scalars(select(LoyaltyRefundDebt)))) == 1
    assert (
        len(
            list(
                session.scalars(
                    select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.reason == "order.refunded")
                )
            )
        )
        == 1
    )
    assert result["state"] == "succeeded"
    session.close()


def test_financial_authority_legacy_wrong_business_expired_revoked(tmp_path):
    provider = Controlled()
    active = {
        "valid": principal(),
        "expired": principal(expires_at=utcnow() - timedelta(seconds=1)),
        "viewer": principal(permissions=frozenset({"finance.read"})),
    }
    app = create_app(
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        seed=True,
        payment_recovery_enabled=False,
        payment_providers={"simulated": provider},
        financial_providers={"simulated": provider},
        financial_authenticator=active.get,
    )
    with TestClient(app) as client:
        with app.state.session_factory() as session:
            body = request(RestaurantCommerceService(session)).model_dump(mode="json")
        order = client.post("/api/restaurants/" + BID + "/orders", json=body).json()
        url = "/api/finance/restaurants/" + BID + "/orders/" + order["id"] + "/refund"
        body = {"idempotency_key": "refund-key", "reason": "Customer refund"}
        for token in ["dev-operator", "expired", "viewer", "missing"]:
            assert (
                client.post(
                    url,
                    json=body,
                    headers={
                        "X-101-Financial-Token": token,
                        "X-101-Operator-Token": "dev-operator",
                    },
                ).status_code
                == 403
            )
        assert (
            client.post(
                url.replace(BID, "other-business"),
                json=body,
                headers={"X-101-Financial-Token": "valid"},
            ).status_code
            == 403
        )
        assert provider.effects == 0
        response = client.post(url, json=body, headers={"X-101-Financial-Token": "valid"})
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "succeeded"
        active.clear()
        assert (
            client.post(url, json=body, headers={"X-101-Financial-Token": "valid"}).status_code
            == 403
        )
        assert provider.effects == 1


def test_paid_lookup_cannot_clear_uncertain_refund_hold(factory):
    session, svc, provider, order = setup(factory)
    provider.lose_refund = True
    unknown = refund(svc, order)
    assert unknown["state"] == "unknown"
    lookup = svc.request_financial_operation(
        BID, order.id, "lookup", "new-lookup", "Check settlement", principal()
    )
    assert lookup["state"] == "succeeded"
    for row in svc.list_payment_reconciliation(BID):
        with pytest.raises(PaymentError):
            svc.resolve_financial_review(
                BID, order.id, row["id"], lookup["id"], "Try clearing hold", principal()
            )
    with pytest.raises(InvalidTransitionError):
        svc.transition_order(order.id, "accepted")
    session.close()


def test_slow_old_lookup_cannot_resolve_new_provider_contradiction(factory):
    session, svc, provider, order = setup(factory)
    original = provider.lookup_payment

    def delayed(**kw):
        evidence = original(**kw)
        with factory() as other:
            other_service = RestaurantCommerceService(other)
            other_service.apply_payment_status(
                evidence.provider_reference,
                "failed",
                provider="simulated",
                event_id="newer-failed-event",
                amount_minor=evidence.amount_minor,
                currency=evidence.currency,
            )
        return evidence

    provider.lookup_payment = delayed
    result = svc.request_financial_operation(
        BID, order.id, "lookup", "slow", "Investigate", principal()
    )
    rows = svc.list_payment_reconciliation(BID)
    contradiction = next(r for r in rows if r["reason"] == "contradictory_payment_notification")
    with pytest.raises(PaymentError):
        svc.resolve_financial_review(
            BID, order.id, contradiction["id"], result["id"], "Old observation", principal()
        )
    session.close()


def test_external_refund_during_lookup_does_not_dispatch_second_refund(factory):
    session, svc, provider, order = setup(factory)

    def lookup(**kwargs):
        with factory() as other:
            RestaurantCommerceService(other).apply_payment_status(
                order.payments[0].provider_reference,
                "refunded",
                provider="simulated",
                event_id="external-refund",
                amount_minor=order.total_minor,
                currency=order.currency,
            )
        return None

    provider.lookup_refund = lookup
    result = refund(svc, order)
    assert result["state"] == "review_required"
    assert provider.calls == provider.effects == 0
    assert svc.order_out(order.id).payment_status == "refunded"
    session.close()


def test_confirmed_no_effect_failed_refund_can_be_withdrawn_with_audit(factory):
    session, svc, provider, order = setup(factory)

    def declined(**kw):
        return RefundObservation(
            kw["order_id"],
            kw["provider_reference"],
            kw["amount_minor"],
            kw["currency"],
            "failed",
            "declined-proof",
            "declined-ref",
        )

    provider.refund = declined
    result = refund(svc, order)
    assert result["state"] == "failed"
    row = svc.list_payment_reconciliation(BID)[0]
    svc.resolve_financial_review(
        BID,
        order.id,
        row["id"],
        result["id"],
        "Withdraw declined request; no money moved",
        principal(),
    )
    assert session.get(FinancialOperation, result["id"]).state == "withdrawn"
    assert svc.transition_order(order.id, "accepted").status == "accepted"
    assert refund(svc, order)["state"] == "withdrawn"
    assert provider.effects == 0
    session.close()


def test_signed_external_refund_compensates_applied_benefits_once(factory):
    from world_model.restaurant_commerce.models import (
        Promotion,
        PromotionRedemption,
        RewardDefinition,
        RewardRedemption,
    )

    session, svc, provider, order = setup(factory)
    row = session.get(Order, order.id)
    account = LoyaltyAccount(
        business_id=BID,
        customer_id=row.customer_id,
        available_points=10,
        lifetime_redeemed_points=5,
    )
    reward = RewardDefinition(
        business_id=BID, name="Synthetic reward", points_cost=5, discount_minor=100
    )
    promo = Promotion(business_id=BID, code="M3B", name="Synthetic promotion", value=100)
    session.add_all([account, reward, promo])
    session.flush()
    redemption = RewardRedemption(
        business_id=BID,
        customer_id=row.customer_id,
        reward_id=reward.id,
        order_id=row.id,
        points_spent=5,
        discount_minor=100,
        status="applied",
    )
    promotion = PromotionRedemption(
        business_id=BID,
        customer_id=row.customer_id,
        promotion_id=promo.id,
        order_id=row.id,
        discount_minor=100,
        status="applied",
    )
    session.add_all([redemption, promotion])
    session.commit()
    for event in ["refund-external", "refund-external", "refund-external-repeat"]:
        svc.apply_payment_status(
            order.payments[0].provider_reference,
            "refunded",
            provider="simulated",
            event_id=event,
            amount_minor=order.total_minor,
            currency=order.currency,
        )
    session.refresh(account)
    assert account.available_points == 15 and account.lifetime_redeemed_points == 0
    assert redemption.status == promotion.status == "released"
    assert (
        len(
            list(
                session.scalars(
                    select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.reason == "order.refunded")
                )
            )
        )
        == 1
    )
    session.close()


def test_stale_refund_worker_cannot_finalize_local_state(factory):
    from sqlalchemy import update

    session, svc, provider, order = setup(factory)

    def takeover():
        with factory() as other:
            other.execute(
                update(FinancialOperation)
                .where(FinancialOperation.order_id == order.id)
                .values(lease_token="new-owner", state="review_required")
            )
            other.commit()

    provider.callback = takeover
    result = refund(svc, order)
    assert result["state"] == "review_required"
    assert svc.order_out(order.id).payment_status == "paid"
    assert provider.effects == 1
    session.close()


def test_populated_m3a_upgrade_preserves_order_and_payment(factory):
    from world_model.restaurant_commerce.db import database_ready
    from world_model.restaurant_commerce.migrations import (
        FINANCIAL_TABLES,
        upgrade_financial_resolution,
    )
    from world_model.restaurant_commerce.models import Base, Payment

    session, svc, provider, order = setup(factory)
    engine = session.get_bind()
    session.close()
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in FINANCIAL_TABLES:
            table.drop(engine)
    assert not database_ready(engine)
    upgrade_financial_resolution(engine)
    upgrade_financial_resolution(engine)
    assert database_ready(engine)
    with factory() as s:
        assert s.get(Order, order.id).payment_status == "paid"
        assert (
            s.scalar(select(Payment).where(Payment.order_id == order.id)).provider_reference
            == order.payments[0].provider_reference
        )
        assert not list(s.scalars(select(FinancialOperation)))


def test_refund_hold_prevents_courier_dispatch(factory):
    session, svc, provider, order = setup(factory)
    provider.lose_refund = True
    refund(svc, order)
    with pytest.raises(InvalidTransitionError, match="Refund intent prevents delivery dispatch"):
        svc.dispatch_delivery(order.id)
    session.close()


def test_future_completed_order_repays_refund_debt_with_ledger(factory):
    session, svc, provider, order = setup(factory)
    customer_id = session.get(Order, order.id).customer_id
    account = LoyaltyAccount(
        business_id=BID, customer_id=customer_id, available_points=2, lifetime_earned_points=10
    )
    session.add(account)
    session.flush()
    session.add(
        LoyaltyLedgerEntry(
            account_id=account.id,
            order_id=order.id,
            delta_points=10,
            reason="order.completed",
            idempotency_key="order-complete:" + order.id,
        )
    )
    session.commit()
    refund(svc, order)
    svc.verified_customer_id = customer_id
    next_order = svc.create_order(BID, request(svc))
    for status in ["accepted", "preparing", "ready", "completed"]:
        svc.transition_order(next_order.id, status)
    session.refresh(account)
    earned = session.scalar(
        select(LoyaltyLedgerEntry).where(
            LoyaltyLedgerEntry.idempotency_key == "order-complete:" + next_order.id
        )
    )
    debt = session.scalar(select(LoyaltyRefundDebt))
    repaid = min(8, earned.delta_points)
    assert debt.remaining_points == 8 - repaid
    assert account.available_points == earned.delta_points - repaid
    assert (
        session.scalar(
            select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.reason == "refund.debt_repaid")
        ).delta_points
        == -repaid
    )
    session.close()
