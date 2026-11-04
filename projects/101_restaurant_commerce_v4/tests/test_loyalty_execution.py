"""Stage 3: real checkout consumers, immutable history, cumulative refunds and races."""

import json
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from test_growth_v2 import pay_and_complete
from test_loyalty_configuration import create, publish
from test_payment_durability_m3 import factory as shared_factory
from test_payment_durability_m3 import request
from world_model.restaurant_commerce.db import database_ready
from world_model.restaurant_commerce.errors import IdempotencyConflictError, ValidationError
from world_model.restaurant_commerce.growth import RestaurantGrowthService
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_execution import (
    ExecutionSelection,
    resolve_refund_allocation,
)
from world_model.restaurant_commerce.loyalty_execution_migrations import upgrade_loyalty_execution
from world_model.restaurant_commerce.loyalty_execution_models import LoyaltyBudget as Budget
from world_model.restaurant_commerce.loyalty_execution_models import (
    LoyaltyOrderSnapshot as Snapshot,
)
from world_model.restaurant_commerce.loyalty_execution_models import LoyaltyOrderState as State
from world_model.restaurant_commerce.loyalty_execution_models import LoyaltyPointLot as Lot
from world_model.restaurant_commerce.loyalty_models import LoyaltyStrategy
from world_model.restaurant_commerce.loyalty_wallet import expire, reconcile
from world_model.restaurant_commerce.models import (
    Customer,
    LoyaltyAccount,
    LoyaltyRefundDebt,
    Order,
    Payment,
    utcnow,
)
from world_model.restaurant_commerce.models import LoyaltyLedgerEntry as Ledger
from world_model.restaurant_commerce.refunds import PaymentRefund, record_refund
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService

factory = shared_factory


@pytest.fixture
def configured(factory):
    upgrade_loyalty_execution(factory.kw["bind"])
    with factory() as session:
        config = LoyaltyConfigurationService(session, "synthetic-operator")
        version = publish(config, create(config, estimated_cost_per_point_minor=10))
        customer = Customer(business_id=BID, name="Synthetic durability", phone="3005550600")
        session.add(customer)
        session.commit()
        return factory, version["version_id"], customer.id


def service(session, version_id, customer_id, *, redeem=False):
    return RestaurantCommerceService(
        session,
        verified_customer_id=customer_id,
        loyalty_execution=ExecutionSelection(version_id, redeem, True, "synthetic_tax_exclusive"),
    )


def balance(session, customer_id):
    return session.scalar(select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id))


def refund(svc, order, amount, *, reference=None, allocation=None):
    payment = svc.session.scalar(select(Payment).where(Payment.order_id == order.id))
    reference = reference or uuid4().hex
    return record_refund(
        svc,
        "simulated",
        {
            "provider_reference": payment.provider_reference,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "refund_reference": reference,
            "refund_amount_minor": amount,
            "event_id": "refund-" + reference,
            **({"loyalty_allocation": allocation} if allocation is not None else {}),
        },
        "{}",
    )


def line_id(session, order):
    return session.get(Order, order.id).items[0].id


def test_complete_duplicate_and_version_pin(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        order = svc.create_order(BID, req)
        snapshot = session.get(Snapshot, order.id)
        assert snapshot.version_id == vid
        original = json.loads(snapshot.document)
        strategy = session.get(
            LoyaltyStrategy,
            session.get(
                __import__(
                    "world_model.restaurant_commerce.loyalty_models",
                    fromlist=["LoyaltyStrategyVersion"],
                ).LoyaltyStrategyVersion,
                vid,
            ).strategy_id,
        )
        strategy.state = "paused"
        session.commit()
        order = pay_and_complete(svc, order)
        account = balance(session, cid)
        expected = original["calculation"]["earning"]["points"]
        assert account.available_points == expected + order.total_minor // 1000
        before = account.available_points
        RestaurantGrowthService(session).award_completed_order(session.get(Order, order.id))
        session.commit()
        assert account.available_points == before
        assert svc.create_order(BID, req).id == order.id
        assert reconcile(session, account)["reconciled"]
        assert session.scalar(select(func.count()).select_from(Lot)) == 1
        for bucket in session.scalars(select(Budget)):
            assert bucket.reserved_minor == 0 and bucket.committed_minor == expected * 10


def test_cumulative_partial_then_full_and_review_hold(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, cid)
        initial = account.available_points
        refund(svc, order, 501, reference="partial-a")
        assert account.available_points == initial
        record = session.scalar(select(PaymentRefund))
        resolve_refund_allocation(
            svc,
            record.id,
            {"lines": {line_id(session, order): 501}, "delivery_fee_minor": 0},
            business_id=BID,
            actor="finance-test",
        )
        session.commit()
        assert account.available_points == 2 * ((order.total_minor - 501) // 1000)
        refund(
            svc,
            order,
            500,
            reference="partial-b",
            allocation={"lines": {line_id(session, order): 500}, "delivery_fee_minor": 0},
        )
        assert account.available_points == 2 * ((order.total_minor - 1001) // 1000)
        refund(svc, order, order.total_minor - 1001, reference="full")
        assert account.available_points == 0
        refund(svc, order, order.total_minor - 1001, reference="full")
        assert reconcile(session, account)["reconciled"]
        assert session.get(State, order.id).status == "refunded"


def test_storage_retention_and_migration_repeatable(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        count = session.scalar(select(func.count()).select_from(Ledger))
    upgrade_loyalty_execution(factory.kw["bind"])
    assert database_ready(factory.kw["bind"], require_loyalty=True)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Ledger)) == count
        for statement in [
            update(Snapshot).values(digest="bad"),
            delete(Snapshot),
            delete(Ledger),
            update(Ledger).values(delta_points=999),
            delete(LoyaltyAccount),
        ]:
            with pytest.raises(DBAPIError):
                session.execute(statement)
                session.commit()
            session.rollback()


def test_disabled_identity_and_budget_fail_atomically(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        svc.loyalty_execution = ExecutionSelection(vid)
        with pytest.raises(ValidationError, match="enablement"):
            svc.create_order(BID, req)
        session.rollback()
        svc = service(session, vid, None)
        with pytest.raises(ValidationError, match="identity"):
            svc.create_order(BID, req)
        session.rollback()
        config = LoyaltyConfigurationService(session, "test")
        small = publish(
            config,
            create(
                config,
                key="small",
                estimated_cost_per_point_minor=10000,
                campaign_budget_minor=1,
                per_customer_budget_minor=1,
            ),
        )
        svc = service(session, small["version_id"], cid)
        with pytest.raises(ValidationError, match="budget"):
            svc.create_order(BID, req)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(Budget)) == 0


def fixed_version(session, *, points=5, cost=1000, **changes):
    config = LoyaltyConfigurationService(session, "test")
    return publish(
        config,
        create(
            config,
            key=uuid4().hex,
            estimated_cost_per_point_minor=10,
            reward={"type": "fixed_value", "points_cost": points, "discount_minor": cost},
            **changes,
        ),
    )["version_id"]


def test_redeem_release_keeps_expiry_and_no_double_credit(configured, monkeypatch):
    factory, vid, cid = configured
    with factory() as session:
        vid = fixed_version(session, expiration_days=1)
        svc = service(session, vid, cid)
        earned_order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        lot = session.scalar(select(Lot))
        svc.loyalty_execution = ExecutionSelection(vid, True, True, "synthetic_tax_exclusive")
        order = svc.create_order(BID, request(svc))
        assert lot.available_points == lot.original_points - 5
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr("world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future)
        growth = RestaurantGrowthService(session)
        account = growth.ensure_account(BID, cid, for_update=True)
        assert expire(session, account) == lot.original_points - 5
        session.commit()
        svc.apply_payment_status(order.payments[0].provider_reference, "failed")
        assert lot.available_points == 0
        assert lot.expired_points == lot.original_points
        before = account.available_points
        svc.apply_payment_status(order.payments[0].provider_reference, "failed")
        assert account.available_points == before
        assert reconcile(session, account)["reconciled"]
        # Refunding already-expired issuance cannot charge the customer a second time.
        refund(svc, earned_order, earned_order.total_minor)
        assert account.available_points == 0
        assert session.scalar(select(LoyaltyRefundDebt)) is None
        assert reconcile(session, account)["reconciled"]


def test_partial_restore_rounding_full_remainder_and_spent_debt(configured):
    factory, vid, cid = configured
    with factory() as session:
        vid = fixed_version(session)
        svc = service(session, vid, cid)
        first = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account = balance(session, cid)
        svc.loyalty_execution = ExecutionSelection(vid, True, True, "synthetic_tax_exclusive")
        second = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        first_state = session.get(State, first.id)
        # Spend all available points with a real, versioned reservation.
        spend_vid = fixed_version(session, points=account.available_points, cost=500)
        svc.loyalty_execution = ExecutionSelection(spend_vid, True, True, "synthetic_tax_exclusive")
        third = svc.create_order(BID, request(svc))
        assert account.available_points == 0
        refund(svc, first, first.total_minor)
        debt = session.scalar(
            select(LoyaltyRefundDebt).where(LoyaltyRefundDebt.order_id == first.id)
        )
        assert debt.remaining_points == first_state.issued_points + first_state.baseline_points
        # Refund the second order in two portions; restored points repay outstanding debt.
        amount = second.total_minor // 2
        refund(
            svc,
            second,
            amount,
            allocation={"lines": {line_id(session, second): amount}, "delivery_fee_minor": 0},
        )
        assert session.get(State, second.id).restored_points == 5 * amount // second.total_minor
        refund(svc, second, second.total_minor - amount)
        assert session.get(State, second.id).restored_points == 5
        svc.apply_payment_status(third.payments[0].provider_reference, "failed")
        assert account.available_points == 0
        assert all(d.remaining_points == 0 for d in session.scalars(select(LoyaltyRefundDebt)))
        assert reconcile(session, account)["reconciled"]


def test_partial_before_completion_and_invalid_allocations(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        order = svc.create_order(BID, request(svc))
        svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        refund(svc, order, 1001)
        for status in ["accepted", "preparing", "ready", "completed"]:
            svc.transition_order(order.id, status)
        assert balance(session, cid).available_points == 0
        record = session.scalar(select(PaymentRefund))
        for allocation in [
            {"lines": {"foreign": 1001}, "delivery_fee_minor": 0},
            {"lines": {line_id(session, order): 1000}, "delivery_fee_minor": 0},
            {"lines": {}, "delivery_fee_minor": 1001},
        ]:
            with pytest.raises(ValidationError):
                resolve_refund_allocation(
                    svc, record.id, allocation, business_id=BID, actor="reviewer"
                )
            session.rollback()
        resolve_refund_allocation(
            svc,
            record.id,
            {"lines": {line_id(session, order): 1001}, "delivery_fee_minor": 0},
            business_id=BID,
            actor="reviewer",
        )
        session.commit()
        assert balance(session, cid).available_points == 2 * ((order.total_minor - 1001) // 1000)
        assert reconcile(session, balance(session, cid))["reconciled"]


@pytest.mark.parametrize("before_completion", [True, False])
def test_refund_rechecks_minimum_on_retained_pre_reward_spend(configured, before_completion):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        total = svc.quote(BID, req.items, customer_phone=req.customer.phone).total_minor
        vid = fixed_version(session, eligibility={"minimum_purchase_minor": total})
        svc = service(session, vid, cid)
        order = svc.create_order(BID, req)
        if before_completion:
            svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        else:
            order = pay_and_complete(svc, order)
        refund(
            svc,
            order,
            1,
            allocation={"lines": {line_id(session, order): 1}, "delivery_fee_minor": 0},
        )
        if before_completion:
            for status in ["accepted", "preparing", "ready", "completed"]:
                svc.transition_order(order.id, status)
        state = session.get(State, order.id)
        assert state.issued_points - state.reversed_points == 0
        assert balance(session, cid).available_points == (order.total_minor - 1) // 1000


def test_legacy_redemption_of_expired_experimental_points_refunds_safely(configured, monkeypatch):
    from world_model.restaurant_commerce.models import RewardDefinition

    factory, vid, cid = configured
    with factory() as session:
        vid = fixed_version(session, expiration_days=1)
        svc = service(session, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        lot = session.scalar(select(Lot))
        reward = RewardDefinition(
            business_id=BID,
            name="Synthetic legacy",
            points_cost=lot.original_points,
            discount_minor=500,
        )
        session.add(reward)
        session.commit()
        svc.loyalty_execution = None
        req = request(svc).model_copy(update={"reward_id": reward.id})
        order = pay_and_complete(svc, svc.create_order(BID, req))
        # Spend every remaining point on an unresolved legacy reservation.
        account = balance(session, cid)
        reward2 = RewardDefinition(
            business_id=BID,
            name="Spend remainder",
            points_cost=account.available_points,
            discount_minor=500,
        )
        session.add(reward2)
        session.commit()
        svc.create_order(BID, request(svc).model_copy(update={"reward_id": reward2.id}))
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr("world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future)
        refund(svc, order, order.total_minor)
        assert account.available_points == 0
        assert (
            session.scalar(select(LoyaltyRefundDebt)).remaining_points == order.total_minor // 1000
        )
        assert reconcile(session, account)["reconciled"]


def test_changed_execution_selection_cannot_replay_order(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        svc.create_order(BID, req)
        svc.loyalty_execution = None
        with pytest.raises(IdempotencyConflictError):
            svc.create_order(BID, req)


def test_normalized_partial_notification_and_staff_review_api(configured):
    from fastapi.testclient import TestClient
    from staff_helpers import staff_headers
    from world_model.restaurant_commerce.api import create_app
    from world_model.restaurant_commerce.schemas import PaymentWebhookIn

    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
        # This is the normalized authenticated adapter seam, not an unsigned HTTP callback.
        body = PaymentWebhookIn(
            event_id="partial-observation",
            provider_reference=payment.provider_reference,
            status="partially_refunded",
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            refund_reference="partial-observation",
            refund_amount_minor=1001,
        )
        svc.receive_payment_notification("simulated", body)
        svc.drain_payment_notifications()
        rid = session.scalar(select(PaymentRefund.id))
        assert rid
        allocated_line = line_id(session, order)
    app = create_app(engine=factory.kw["bind"], payment_recovery_enabled=False)
    # PG factory has a private search_path, so inject the same session dependency factory.
    app.state.session_factory = factory
    with TestClient(app) as client:
        url = f"/api/finance/restaurants/{BID}/loyalty-refunds/{rid}/allocation"
        payload = {"lines": {allocated_line: 1001}, "delivery_fee_minor": 0}
        assert client.post(url, json=payload).status_code in {401, 403}
        headers = staff_headers(client, business_id=BID)
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 200, response.text
        assert client.post(url, headers=headers, json=payload).status_code == 200
        assert client.post(url, json=payload).status_code == 403
        assert (
            client.post(
                url.replace(BID, "another-business"), headers=headers, json=payload
            ).status_code
            == 403
        )
        assert client.post(
            url, headers=headers, json={**payload, "delivery_fee_minor": 1}
        ).status_code in {400, 409, 422}
        viewer = staff_headers(client, business_id=BID, role="viewer", name="refund.viewer")
        assert client.post(url, headers=viewer, json=payload).status_code == 403
    with factory() as session:
        assert balance(session, cid).available_points == 2 * ((order.total_minor - 1001) // 1000)


def run_pair(function):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(function, index, barrier) for index in range(2)]
        return [future.result(timeout=30) for future in futures]


def pg_only(factory):
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock concurrency proof")


def test_concurrent_redemptions_refresh_cached_balance(configured):
    factory, vid, cid = configured
    pg_only(factory)
    with factory() as session:
        svc = service(session, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        available = balance(session, cid).available_points
        vid = fixed_version(session, points=available)

    def worker(index, barrier):
        with factory() as session:
            cached = balance(session, cid)
            assert cached.available_points == available
            session.commit()
            svc = service(session, vid, cid, redeem=True)
            req = request(svc)
            barrier.wait(timeout=10)
            from sqlalchemy.orm.exc import StaleDataError

            for attempt in range(2):
                try:
                    return svc.create_order(BID, req).id
                except StaleDataError:
                    # Existing contact revision fencing can win before the wallet lock.
                    session.rollback()
                    if attempt:
                        raise
                except ValidationError as exc:
                    session.rollback()
                    assert "insufficient_points" in str(exc)
                    return None

    results = run_pair(worker)
    assert sum(value is not None for value in results) == 1
    with factory() as session:
        assert balance(session, cid).available_points == 0
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_concurrent_last_campaign_budget_across_customers(configured):
    factory, vid, cid = configured
    pg_only(factory)
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        points = svc.quote(BID, req.items, customer_phone=req.customer.phone).total_minor // 1000
        config = LoyaltyConfigurationService(session, "test")
        vid = publish(
            config,
            create(
                config,
                key="last-budget",
                estimated_cost_per_point_minor=10,
                campaign_budget_minor=points * 10,
                per_customer_budget_minor=points * 10,
            ),
        )["version_id"]
        second = Customer(business_id=BID, name="Other synthetic", phone="3005550601")
        session.add(second)
        session.commit()
        customers = [(cid, "3005550600"), (second.id, second.phone)]

    def worker(index, barrier):
        with factory() as session:
            customer, phone = customers[index]
            svc = service(session, vid, customer)
            req = request(svc)
            req.customer.phone = phone
            barrier.wait(timeout=10)
            try:
                return svc.create_order(BID, req).id
            except ValidationError as exc:
                session.rollback()
                assert "budget" in str(exc)
                return None

    assert sum(value is not None for value in run_pair(worker)) == 1
    with factory() as session:
        bucket = session.scalar(select(Budget).where(Budget.scope == "*"))
        assert bucket.reserved_minor == points * 10
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 1


def test_concurrent_completion_and_partial_refund(configured):
    factory, vid, cid = configured
    pg_only(factory)
    with factory() as session:
        svc = service(session, vid, cid)
        order = svc.create_order(BID, request(svc))
        svc.apply_payment_status(order.payments[0].provider_reference, "paid")
        for status in ["accepted", "preparing", "ready"]:
            svc.transition_order(order.id, status)
        line = line_id(session, order)

    def worker(index, barrier):
        with factory() as session:
            svc = service(session, vid, cid)
            barrier.wait(timeout=10)
            if index:
                return refund(
                    svc, order, 1001, allocation={"lines": {line: 1001}, "delivery_fee_minor": 0}
                ).id
            return svc.transition_order(order.id, "completed").id

    assert run_pair(worker) == [order.id, order.id]
    with factory() as session:
        assert balance(session, cid).available_points == 2 * ((order.total_minor - 1001) // 1000)
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_cached_projection_after_other_session_refund(configured):
    factory, vid, cid = configured
    with factory() as cached:
        svc = service(cached, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        state = cached.get(State, order.id)
        account = balance(cached, cid)
        line = line_id(cached, order)
        cached.commit()
        with factory() as other:
            refund(
                service(other, vid, cid),
                order,
                501,
                allocation={"lines": {line: 501}, "delivery_fee_minor": 0},
            )
        refund(svc, order, 500, allocation={"lines": {line: 500}, "delivery_fee_minor": 0})
        assert account.available_points == 2 * ((order.total_minor - 1001) // 1000)
        assert (
            state.reversed_points == order.total_minor // 1000 - (order.total_minor - 1001) // 1000
        )
        assert reconcile(cached, account)["reconciled"]


def test_populated_upgrade_keeps_legacy_unknown_and_detects_partial_schema(factory):
    from sqlalchemy import text
    from world_model.restaurant_commerce.db import init_schema
    from world_model.restaurant_commerce.loyalty_execution_migrations import SQLITE

    with factory() as session:
        customer = Customer(business_id=BID, name="Legacy", phone="3005550600")
        session.add(customer)
        session.flush()
        svc = RestaurantCommerceService(session, verified_customer_id=customer.id)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        account_id = balance(session, customer.id).id
        before = balance(session, customer.id).available_points
    upgrade_loyalty_execution(factory.kw["bind"])
    with factory() as session:
        account = session.get(LoyaltyAccount, account_id)
        result = reconcile(session, account)
        assert result["reconciled"] and result["legacy_unattributed_points"] == before
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 0
    with factory.kw["bind"].begin() as conn:
        name = next(iter(SQLITE))
        if conn.dialect.name == "sqlite":
            conn.execute(text("DROP TRIGGER " + name))
        else:
            from world_model.restaurant_commerce.loyalty_execution_migrations import POSTGRES

            conn.execute(text("DROP TRIGGER " + name + " ON " + POSTGRES[name][0]))
    assert not database_ready(factory.kw["bind"])
    with pytest.raises(RuntimeError):
        upgrade_loyalty_execution(factory.kw["bind"])
    with pytest.raises(RuntimeError):
        init_schema(factory.kw["bind"])


def test_lot_origin_immutable_and_expiration_batch_idempotent(configured):
    from world_model.restaurant_commerce.loyalty_wallet import expire_due_accounts

    factory, vid, cid = configured
    with factory() as session:
        vid = fixed_version(session, expiration_days=1)
        svc = service(session, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        for mutation in [
            delete(Lot),
            update(Lot).values(cost_per_point_minor=0),
            update(Lot).values(expires_at=None),
            update(Lot).values(original_points=999),
        ]:
            with pytest.raises(DBAPIError):
                session.execute(mutation)
                session.commit()
            session.rollback()
        future = utcnow() + timedelta(days=2)
        result = expire_due_accounts(session, at=future)
        session.commit()
        assert result["expired_points"] > 0
        assert expire_due_accounts(session, at=future) == {"accounts": 0, "expired_points": 0}
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_concurrent_expiration_and_cancellation(configured, monkeypatch):
    from world_model.restaurant_commerce.loyalty_wallet import expire_due_accounts

    factory, vid, cid = configured
    pg_only(factory)
    with factory() as session:
        vid = fixed_version(session, expiration_days=1)
        svc = service(session, vid, cid)
        first = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        svc.loyalty_execution = ExecutionSelection(vid, True, True, "synthetic_tax_exclusive")
        second = svc.create_order(BID, request(svc))
    future = utcnow() + timedelta(days=2)
    monkeypatch.setattr("world_model.restaurant_commerce.loyalty_wallet.utcnow", lambda: future)

    def worker(index, barrier):
        with factory() as session:
            barrier.wait(timeout=10)
            if index:
                expire_due_accounts(session, at=future)
                session.commit()
            else:
                service(session, vid, cid).apply_payment_status(
                    second.payments[0].provider_reference, "failed"
                )
            return True

    assert run_pair(worker) == [True, True]
    with factory() as session:
        assert balance(session, cid).available_points == first.total_minor // 1000
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_edit_new_version_preserves_order_and_shared_budget(configured):
    from test_loyalty_configuration import document
    from world_model.restaurant_commerce.loyalty_schemas import StrategyEdit

    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        amount = (
            svc.quote(BID, req.items, customer_phone=req.customer.phone).total_minor // 1000 * 10
        )
        config = LoyaltyConfigurationService(session, "test")
        draft = create(
            config,
            key="version-budget",
            estimated_cost_per_point_minor=10,
            campaign_budget_minor=amount,
            per_customer_budget_minor=amount,
        )
        vid = publish(config, draft)["version_id"]
        svc = service(session, vid, cid)
        first = svc.create_order(BID, req)
        current = config.get("programs", BID, draft["id"])
        edited = config.edit(
            "programs",
            BID,
            draft["id"],
            StrategyEdit(
                expected_revision=current["revision"],
                document=document(
                    estimated_cost_per_point_minor=10,
                    campaign_budget_minor=amount,
                    per_customer_budget_minor=amount,
                    earning={"type": "points", "spend_minor_per_point": 2000},
                ),
            ),
        )
        new_vid = publish(config, edited)["version_id"]
        svc.loyalty_execution = ExecutionSelection(new_vid, False, True, "synthetic_tax_exclusive")
        with pytest.raises(ValidationError, match="budget"):
            svc.create_order(BID, request(svc))
        session.rollback()
        pay_and_complete(svc, first)
        assert session.get(Snapshot, first.id).version_id == vid
        assert session.get(State, first.id).issued_points == first.total_minor // 1000


def test_excluded_product_partial_refund_does_not_reverse_incremental_points(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        req = request(svc)
        items = [
            item
            for menu in svc.storefront(BID).menus
            for category in menu.categories
            for item in category.items
            if not item.modifier_groups
        ]
        assert len(items) >= 2
        req.items.append(req.items[0].model_copy(update={"menu_item_id": items[1].id}))
        for item in req.items:
            item.quantity = 3
        req.promo_code = "DIRECTO10"
        config = LoyaltyConfigurationService(session, "test")
        vid = publish(
            config,
            create(
                config,
                key="exclusions",
                estimated_cost_per_point_minor=10,
                stack_with_promotions=True,
                eligibility={"excluded_product_ids": [items[1].id]},
            ),
        )["version_id"]
        svc = service(session, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, req))
        data = json.loads(session.get(Snapshot, order.id).document)
        excluded = next(line for line in data["calculation"]["lines"] if not line["included"])
        line = data["line_ids"][excluded["line_id"]]
        initial = session.get(State, order.id).issued_points
        amount = excluded["net_item_minor"]
        refund(svc, order, amount, allocation={"lines": {line: amount}, "delivery_fee_minor": 0})
        assert session.get(State, order.id).reversed_points == 0
        assert (
            balance(session, cid).available_points == initial + (order.total_minor - amount) // 1000
        )
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_lot_restoration_refreshes_cached_projection(configured):
    factory, vid, cid = configured
    with factory() as cached:
        vid = fixed_version(cached, points=2)
        svc = service(cached, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        svc.loyalty_execution = ExecutionSelection(vid, True, True, "synthetic_tax_exclusive")
        first = svc.create_order(BID, request(svc))
        second = svc.create_order(BID, request(svc))
        lot = cached.scalar(select(Lot))
        original = lot.original_points
        cached.commit()
        with factory() as other:
            service(other, vid, cid).apply_payment_status(
                first.payments[0].provider_reference, "failed"
            )
        svc.apply_payment_status(second.payments[0].provider_reference, "failed")
        assert lot.available_points == original
        assert reconcile(cached, balance(cached, cid))["reconciled"]


def test_immediate_paid_and_delivery_consume_versioned_lifecycle(configured):
    from dataclasses import replace

    from test_delivery_v3 import destination
    from world_model.restaurant_commerce.payments import SimulatedPaymentProvider

    factory, vid, cid = configured

    class Paid(SimulatedPaymentProvider):
        def create_checkout(self, **kwargs):
            return replace(super().create_checkout(**kwargs), status="paid")

    with factory() as session:
        svc = service(session, vid, cid)
        svc.payment_providers = {"simulated": Paid()}
        quote = svc.create_delivery_quote(BID, destination())
        req = request(svc).model_copy(
            update={"fulfillment_type": "delivery", "delivery_quote_id": quote.id}
        )
        order = svc.create_order(BID, req)
        assert session.get(State, order.id).status == "applied"
        svc.transition_order(order.id, "accepted")
        delivery = svc.dispatch_delivery(order.id)
        for status in ["preparing", "ready"]:
            svc.transition_order(order.id, status)
        for status in ["courier_assigned", "picked_up", "delivered"]:
            svc.apply_delivery_status(delivery.provider_delivery_reference, status)
        assert session.get(State, order.id).completed
        assert balance(session, cid).available_points == 2 * (
            (order.total_minor - order.delivery_fee_minor) // 1000
        )
        refund(
            svc,
            order,
            order.delivery_fee_minor,
            allocation={"lines": {}, "delivery_fee_minor": order.delivery_fee_minor},
        )
        assert session.get(State, order.id).reversed_points == 0


def test_zero_rate_legacy_baseline_remains_disabled_for_earning(configured):
    factory, vid, cid = configured
    with factory() as session:
        baseline = RestaurantGrowthService(session).ensure_program(BID)
        baseline.enabled, baseline.spend_minor_per_point = True, 0
        session.commit()
        svc = service(session, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        assert balance(session, cid).available_points == order.total_minor // 1000
        refund(svc, order, order.total_minor)
        assert balance(session, cid).available_points == 0
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_cancel_then_late_paid_refund_never_returns_points_twice(configured):
    factory, vid, cid = configured
    with factory() as session:
        vid = fixed_version(session)
        svc = service(session, vid, cid)
        pay_and_complete(svc, svc.create_order(BID, request(svc)))
        available = balance(session, cid).available_points
        svc.loyalty_execution = ExecutionSelection(vid, True, True, "synthetic_tax_exclusive")
        order = svc.create_order(BID, request(svc))
        svc.transition_order(order.id, "cancelled")
        assert balance(session, cid).available_points == available
        svc.apply_payment_status(order.payments[0].provider_reference, "paid", event_id="late-paid")
        refund(
            svc,
            order,
            500,
            allocation={"lines": {line_id(session, order): 500}, "delivery_fee_minor": 0},
        )
        refund(svc, order, order.total_minor - 500)
        assert balance(session, cid).available_points == available
        assert balance(session, cid).lifetime_redeemed_points == 0
        assert reconcile(session, balance(session, cid))["reconciled"]


def test_installed_execution_readiness_preserves_catalogue_query_bound(configured):
    from sqlalchemy import event

    factory, vid, cid = configured
    pg_only(factory)
    engine = factory.kw["bind"]
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        assert database_ready(engine, require_loyalty=True)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(queries) <= 20, queries


def test_large_cumulative_refund_identity_fits_postgres_ledger_key(configured):
    factory, vid, cid = configured
    with factory() as session:
        svc = service(session, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        debt = LoyaltyRefundDebt(
            order_id=order.id, account_id=balance(session, cid).id, remaining_points=1
        )
        session.add(debt)
        session.commit()
        growth = RestaurantGrowthService(session)
        account = growth.ensure_account(BID, cid, for_update=True)
        source = f"loyalty-refund:{order.id}:1:500000000:500000000:1000000000"
        growth._settle_refund_debt(account, order.id, source)
        session.commit()
        assert debt.remaining_points == 0
        entry = session.scalar(select(Ledger).where(Ledger.reason == "refund.debt_repaid"))
        assert len(entry.idempotency_key) <= 160
        assert reconcile(session, account)["reconciled"]
