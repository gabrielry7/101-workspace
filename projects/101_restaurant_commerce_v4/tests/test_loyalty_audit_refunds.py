"""101-033: refund accounting must not depend on scheduling or policy edits."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select
from test_growth_v2 import pay_and_complete
from test_loyalty_execution import balance, fixed_version, refund, service
from test_loyalty_execution import (
    configured as configured,  # noqa: PLC0414 - pytest fixture re-export
)
from test_loyalty_execution import (
    factory as factory,  # noqa: PLC0414 - pytest fixture re-export
)
from test_payment_durability_m3 import request

from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.loyalty_execution import ExecutionSelection
from world_model.restaurant_commerce.loyalty_wallet import expire, reconcile
from world_model.restaurant_commerce.models import LoyaltyRefundDebt, Order, utcnow
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService


def debt_total(session):
    return session.scalar(
        select(func.coalesce(func.sum(LoyaltyRefundDebt.remaining_points), 0))
    )


def assert_reconciled(session, account):
    from world_model.restaurant_commerce.loyalty_execution_migrations import installed
    from world_model.restaurant_commerce.models import LoyaltyLedgerEntry

    session.flush()
    assert account.available_points == session.scalar(
        select(func.coalesce(func.sum(LoyaltyLedgerEntry.delta_points), 0)).where(
            LoyaltyLedgerEntry.account_id == account.id
        )
    )
    if installed(session):
        assert reconcile(session, account)["reconciled"]


@pytest.mark.parametrize("refund_before_completion", [False, True])
def test_ordinary_partial_refunds_preserve_original_rate(
    configured, refund_before_completion
):
    sessions, _, cid = configured
    with sessions() as session:
        svc = RestaurantCommerceService(session, verified_customer_id=cid)
        order = svc.create_order(BID, request(svc))
        if refund_before_completion:
            svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        else:
            pay_and_complete(svc, order)
        program = RestaurantGrowthService(session).ensure_program(BID)
        program.spend_minor_per_point = 100
        session.commit()
        refund(svc, order, 5000, reference="first")
        refund(svc, order, 5000, reference="first")
        if refund_before_completion:
            pay_and_complete(svc, order)
        account = balance(session, cid)
        assert account.available_points == (order.total_minor - 5000) // 1000
        refund(svc, order, order.total_minor - 5000, reference="rest")
        assert (
            account.available_points
            == account.lifetime_earned_points
            == debt_total(session)
            == 0
        )
        assert_reconciled(session, account)


@pytest.mark.parametrize("maintain_first", [False, True])
def test_expired_points_cannot_repay_other_refund(
    configured, monkeypatch, maintain_first
):
    sessions, vid, cid = configured
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        svc = service(session, vid, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, cid)
        points = account.available_points
        spend = fixed_version(session, points=points, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spend, True, True, "synthetic_tax_exclusive"
        )
        svc.create_order(BID, request(svc))
        expires = fixed_version(session, expiration_days=1)
        svc.loyalty_execution = ExecutionSelection(
            expires, False, True, "synthetic_tax_exclusive"
        )
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future
        )
        if maintain_first:
            expire(session, account)
            session.commit()
        refund(svc, source, source.total_minor, reference="source")
        assert debt_total(session) == points
        refund(svc, source, source.total_minor, reference="source")
        assert debt_total(session) == points
        assert_reconciled(session, account)


@pytest.mark.parametrize("source_first", [False, True])
@pytest.mark.parametrize("repay_between", [False, True])
def test_expired_source_return_retires_only_its_clawback(
    configured, monkeypatch, source_first, repay_between
):
    sessions, vid, cid = configured
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        expiry = fixed_version(session, expiration_days=1)
        svc = service(session, expiry, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, cid)
        points = account.available_points
        spend = fixed_version(session, points=points, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spend, True, True, "synthetic_tax_exclusive"
        )
        spent = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future
        )
        first, last = (source, spent) if source_first else (spent, source)
        expire(session, account)
        refund(svc, first, first.total_minor, reference="first")
        if repay_between:
            svc.loyalty_execution = ExecutionSelection(
                vid, False, True, "synthetic_tax_exclusive"
            )
            pay_and_complete(svc, svc.create_order(BID, request(svc)))
        expire(session, account)
        refund(svc, last, last.total_minor, reference="last")
        refund(svc, last, last.total_minor, reference="last")
        assert debt_total(session) == 0
        assert account.available_points == (points if repay_between else 0)
        assert_reconciled(session, account)


@pytest.mark.parametrize("chunks", [[5000], [2500, 2500]])
def test_baseline_spent_points_partial_then_full_debt_is_cumulative(factory, chunks):
    from world_model.restaurant_commerce.models import Customer, RewardDefinition

    with factory() as session:
        customer = Customer(business_id=BID, phone="3005550600", name="Synthetic")
        session.add(customer)
        session.commit()
        svc = RestaurantCommerceService(session, verified_customer_id=customer.id)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, customer.id)
        issued = account.available_points
        reward = RewardDefinition(
            business_id=BID,
            name="Synthetic",
            points_cost=issued,
            discount_minor=1000,
            minimum_order_minor=0,
        )
        session.add(reward)
        session.commit()
        r = request(svc)
        r.reward_id = reward.id
        spending = svc.create_order(BID, r)
        assert account.available_points == 0
        for index, amount in enumerate(chunks):
            refund(svc, order, amount, reference="part-" + str(index))
            refund(svc, order, amount, reference="part-" + str(index))
        assert debt_total(session) == issued - (order.total_minor - 5000) // 1000
        refund(svc, order, order.total_minor - 5000, reference="rest")
        assert debt_total(session) == issued
        svc.apply_payment_status(spending.payments[0].provider_reference, "failed")
        assert debt_total(session) == account.available_points == 0
        assert_reconciled(session, account)


def test_missing_historical_policy_holds_redemption_and_preserves_money(configured):
    import json

    from world_model.restaurant_commerce.errors import ValidationError
    from world_model.restaurant_commerce.loyalty_baseline import pending
    from world_model.restaurant_commerce.models import RewardDefinition

    sessions, _, cid = configured
    with sessions() as session:
        svc = RestaurantCommerceService(session, verified_customer_id=cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        raw = session.get(Order, order.id)
        snapshot = json.loads(raw.customer_snapshot_json)
        snapshot.pop("baseline_policy")
        raw.customer_snapshot_json = json.dumps(snapshot)
        session.commit()
        refund(svc, order, 5000)
        account = balance(session, cid)
        assert pending(session, account)
        reward = RewardDefinition(
            business_id=BID,
            name="Synthetic",
            points_cost=1,
            discount_minor=100,
            minimum_order_minor=0,
        )
        session.add(reward)
        session.commit()
        r = request(svc)
        r.reward_id = reward.id
        with pytest.raises(ValidationError, match="review"):
            svc.create_order(BID, r)
        session.rollback()
        refund(svc, order, order.total_minor - 5000)
        assert not pending(session, account)
        assert account.available_points == 0


def test_delivery_allocation_hold_and_authorized_resolution(factory):
    from fastapi.testclient import TestClient
    from staff_helpers import staff_headers
    from test_delivery_v3 import destination

    from world_model.restaurant_commerce.api import create_app
    from world_model.restaurant_commerce.loyalty_baseline import pending
    from world_model.restaurant_commerce.models import Customer
    from world_model.restaurant_commerce.refunds import PaymentRefund

    with factory() as session:
        customer = Customer(business_id=BID, phone="3005550600", name="Synthetic")
        session.add(customer)
        session.commit()
        svc = RestaurantCommerceService(session, verified_customer_id=customer.id)
        quote = svc.create_delivery_quote(BID, destination())
        r = request(svc)
        r.fulfillment_type = "delivery"
        r.delivery_quote_id = quote.id
        order = svc.create_order(BID, r)
        svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        svc.transition_order(order.id, "accepted")
        delivery = svc.dispatch_delivery(order.id)
        svc.transition_order(order.id, "preparing")
        svc.transition_order(order.id, "ready")
        svc.apply_delivery_status(delivery.provider_delivery_reference, "picked_up")
        svc.apply_delivery_status(delivery.provider_delivery_reference, "delivered")
        account = balance(session, customer.id)
        original = account.available_points
        refund(svc, order, 5000, reference="delivery")
        assert pending(session, account) and account.available_points == original
        refund_row = session.scalar(
            select(PaymentRefund).where(PaymentRefund.reference == "delivery")
        )
        line = session.get(Order, order.id).items[0].id
        allocation = {"lines": {line: 4000}, "delivery_fee_minor": 1000}
        rid = refund_row.id
        session.commit()
        app = create_app(engine=factory.kw["bind"], payment_recovery_enabled=False)
        app.state.session_factory = factory
        with TestClient(app) as client:
            url = f"/api/finance/restaurants/{BID}/loyalty-refunds/{rid}/allocation"
            assert client.post(url, json=allocation).status_code in {401, 403}
            headers = staff_headers(client, business_id=BID)
            response = client.post(url, headers=headers, json=allocation)
            assert response.status_code == 200, response.text
            assert client.post(url, headers=headers, json=allocation).status_code == 200
            assert (
                client.post(
                    url.replace(BID, "foreign-business"),
                    headers=headers,
                    json=allocation,
                ).status_code
                == 403
            )
            changed = {"lines": {line: 5000}, "delivery_fee_minor": 0}
            assert client.post(url, headers=headers, json=changed).status_code == 422
        session.expire_all()
        assert not pending(session, account)
        assert (
            account.available_points
            == (order.total_minor - order.delivery_fee_minor - 4000) // 1000
        )
        refund(svc, order, 5000, reference="delivery", allocation=allocation)
        assert_reconciled(session, account)


@pytest.mark.parametrize("spend_points", [5, 11])
def test_expired_return_unwinds_latest_recovery_and_replays_prefix(
    configured, monkeypatch, spend_points
):
    from world_model.restaurant_commerce.loyalty_execution_models import (
        LoyaltyOrderState as State,
    )

    sessions, vid, cid = configured
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        expiry = fixed_version(session, expiration_days=1)
        svc = service(session, expiry, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, cid)
        spend = fixed_version(session, points=spend_points, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spend, True, True, "synthetic_tax_exclusive"
        )
        spent = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        # Refund while the unspent source remainder is still valid. It is recovered
        # before later earnings repay the consumed portion's debt.
        refund(svc, source, source.total_minor)
        assert debt_total(session) == spend_points
        svc.loyalty_execution = ExecutionSelection(
            vid, False, True, "synthetic_tax_exclusive"
        )
        later = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        assert debt_total(session) == 0
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future
        )
        half = spent.total_minor // 2
        line = session.get(Order, spent.id).items[0].id
        allocation = {"lines": {line: half}, "delivery_fee_minor": 0}
        refund(svc, spent, half, reference="half", allocation=allocation)
        first_balance = account.available_points
        refund(svc, spent, half, reference="half", allocation=allocation)
        assert account.available_points == first_balance
        refund(svc, spent, spent.total_minor - half, reference="remaining")
        assert account.available_points == 11 and debt_total(session) == 0
        assert_reconciled(session, account)
        # Retiring A never forgives a later order's independent liability.
        refund(svc, later, later.total_minor)
        assert account.available_points == debt_total(session) == 0
        assert session.get(State, source.id).reversed_points == 11
        assert_reconciled(session, account)


def test_postgres_concurrent_source_refund_and_expired_return(configured, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import text
    from test_loyalty_execution import pg_only

    sessions, vid, cid = configured
    pg_only(sessions)
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        expiry = fixed_version(session, expiration_days=1)
        svc = service(session, expiry, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        spend = fixed_version(session, points=11, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spend, True, True, "synthetic_tax_exclusive"
        )
        spent = pay_and_complete(svc, svc.create_order(BID, request(svc)))
    future = utcnow() + timedelta(days=2)
    monkeypatch.setattr(
        "world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future
    )
    barrier = Barrier(2)

    def worker(order):
        with sessions() as session:
            session.execute(text("SET lock_timeout = '5s'"))
            session.execute(text("SET statement_timeout = '10s'"))
            svc = service(session, vid, cid)
            barrier.wait(timeout=10)
            refund(svc, order, order.total_minor, reference=order.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, [source, spent]))
    with sessions() as session:
        account = balance(session, cid)
        assert account.available_points == debt_total(session) == 0
        assert_reconciled(session, account)


def test_postgres_baseline_completion_races_partial_refund(configured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from test_loyalty_execution import pg_only

    sessions, _, cid = configured
    pg_only(sessions)
    with sessions() as session:
        svc = RestaurantCommerceService(session, verified_customer_id=cid)
        order = svc.create_order(BID, request(svc))
        svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        for status in ["accepted", "preparing", "ready"]:
            svc.transition_order(order.id, status)
    barrier = Barrier(2)

    def worker(action):
        with sessions() as session:
            svc = RestaurantCommerceService(session, verified_customer_id=cid)
            barrier.wait(timeout=10)
            if action == "complete":
                svc.transition_order(order.id, "completed")
            else:
                refund(svc, order, 5000, reference="racing-partial")

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, ["complete", "refund"]))
    with sessions() as session:
        assert (
            balance(session, cid).available_points == (order.total_minor - 5000) // 1000
        )
        assert debt_total(session) == 0


def test_return_before_expiry_preserves_repaid_points_provenance(
    configured, monkeypatch
):
    sessions, vid, cid = configured
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        expiring = fixed_version(session, expiration_days=1)
        svc = service(session, expiring, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        spent_version = fixed_version(session, points=11, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spent_version, True, True, "synthetic_tax_exclusive"
        )
        spending = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        refund(svc, source, source.total_minor)
        svc.loyalty_execution = ExecutionSelection(
            vid, False, True, "synthetic_tax_exclusive"
        )
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        assert debt_total(session) == 0
        refund(svc, spending, spending.total_minor)
        account = balance(session, cid)
        assert account.available_points == 11
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future
        )
        expire(session, account)
        # The returned entitlement belongs to the later nonexpiring earning, not
        # the already-refunded source's original expiring grant.
        assert account.available_points == 11
        assert_reconciled(session, account)


def test_untraceable_historical_repayment_preserves_notification_for_review(
    configured, monkeypatch
):
    from world_model.restaurant_commerce.models import Payment, PaymentNotificationInbox
    from world_model.restaurant_commerce.schemas import PaymentWebhookIn

    sessions, vid, cid = configured
    with sessions() as session:
        RestaurantGrowthService(session).ensure_program(BID).enabled = False
        session.commit()
        expiring = fixed_version(session, expiration_days=1)
        svc = service(session, expiring, cid)
        source = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        spent_version = fixed_version(session, points=11, earning=None)
        svc.loyalty_execution = ExecutionSelection(
            spent_version, True, True, "synthetic_tax_exclusive"
        )
        spending = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        refund(svc, source, source.total_minor)
        original_settle = RestaurantGrowthService._settle_refund_debt
        # Simulate the pre-upgrade writer: hashed repayment key and no execution
        # event tying the recovery to its source. No protected rows are rewritten.
        with monkeypatch.context() as old_writer:
            old_writer.setattr(
                "world_model.restaurant_commerce.loyalty_retirement.record_repayment",
                lambda *args: None,
            )
            old_writer.setattr(
                RestaurantGrowthService,
                "_settle_refund_debt",
                lambda self, account, order_id, source: original_settle(
                    self, account, order_id, source + "x" * 200
                ),
            )
            svc.loyalty_execution = ExecutionSelection(
                vid, False, True, "synthetic_tax_exclusive"
            )
            pay_and_complete(svc, svc.create_order(BID, request(svc)))
        payment = session.scalar(select(Payment).where(Payment.order_id == spending.id))
        from world_model.restaurant_commerce.errors import ValidationError

        with pytest.raises(ValidationError, match="provenance"):
            svc.receive_payment_notification(
                "simulated",
                PaymentWebhookIn(
                    event_id="historical-review",
                    provider_reference=payment.provider_reference,
                    status="refunded",
                    amount_minor=payment.amount_minor,
                    currency=payment.currency,
                ),
            )
        session.rollback()
        svc.drain_payment_notifications()
        notification = session.scalar(
            select(PaymentNotificationInbox).where(
                PaymentNotificationInbox.event_id == "historical-review"
            )
        )
        assert notification.state == "review_required"
        assert '"refunded"' in notification.payload_json
        assert session.get(Order, spending.id).payment_status == "paid"
        assert balance(session, cid).available_points == 0
        assert_reconciled(session, balance(session, cid))


def test_unverified_refund_cannot_hold_verified_customers_wallet(configured):
    from world_model.restaurant_commerce.loyalty_baseline import pending

    sessions, _, cid = configured
    with sessions() as session:
        verified = RestaurantCommerceService(session, verified_customer_id=cid)
        pay_and_complete(verified, verified.create_order(BID, request(verified)))
        account = balance(session, cid)
        unverified = RestaurantCommerceService(session)
        guest_order = pay_and_complete(
            unverified, unverified.create_order(BID, request(unverified))
        )
        refund(unverified, guest_order, 5000)
        assert not pending(session, account)
        assert account.available_points == 11
        assert_reconciled(session, account)
