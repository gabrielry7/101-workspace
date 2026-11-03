"""Deterministic PostgreSQL admission/manager-edit contracts for supported profiles."""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

import pytest
from sqlalchemy import func, select, text
from test_financial_resolution_m3b import principal
from test_operations_m5 import prepare, settings
from test_payment_durability_m3 import factory as factory
from test_payment_durability_m3 import request as order_request
from world_model.restaurant_commerce.errors import IdempotencyConflictError, ValidationError
from world_model.restaurant_commerce.models import ItemStock, MenuItem, Order, PaymentIntent
from world_model.restaurant_commerce.operations import StockSettings
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService as Service


@pytest.fixture
def pg(factory):
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip(
            "Requires actual disposable PostgreSQL; SQLite cannot prove row-lock concurrency"
        )
    return factory


def stock(svc, item, remaining, *, version=0, sold_out=False):
    return svc.save_item_stock(
        BID,
        item,
        StockSettings(
            expected_version=version,
            remaining=remaining,
            sold_out=sold_out,
            reason="Synthetic concurrency test",
        ),
        principal(),
    )


def make_body(factory, *, remaining=None, policy=False):
    with factory() as s:
        svc = Service(s)
        body = order_request(svc, key="first")
        if remaining is not None:
            stock(svc, body.items[0].menu_item_id, remaining)
        if policy:
            svc.save_operations_settings(
                BID, settings().model_copy(update={"scheduled": False}), principal()
            )
        return body


def buy(factory, body, cls=Service, business=BID):
    with factory() as s:
        try:
            return cls(s).create_order(business, body).id
        except (ValidationError, IdempotencyConflictError) as e:
            s.rollback()
            return type(e).__name__


def holding(entered, release):
    class Held(Service):
        def allocate_pickup_and_stock(self, profile, request):
            super().allocate_pickup_and_stock(profile, request)
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Test failed to release held admission")

    return Held


def wait_blocked(factory):
    deadline = time.monotonic() + 4
    with factory() as s:
        while time.monotonic() < deadline:
            n = s.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND cardinality(pg_blocking_pids(pid))>0"
                )
            )
            s.rollback()
            if n:
                return
            time.sleep(0.02)
    raise AssertionError("Expected real PostgreSQL blocker not observed")


@pytest.mark.parametrize(
    "profile", ["untracked", "untracked_policy", "different_item", "different_slot"]
)
def test_independent_allocations_do_not_queue_behind_order(pg, profile):
    body = (
        prepare(pg, capacity=2)
        if profile == "different_slot"
        else make_body(
            pg,
            policy=profile == "untracked_policy",
            remaining=1 if profile == "different_item" else None,
        )
    )
    second = body.model_copy(
        update={
            "idempotency_key": "second",
            "customer": body.customer.model_copy(update={"phone": "3005550601"}),
        }
    )
    with pg() as s:
        svc = Service(s)
        if profile == "different_item":
            original = s.get(MenuItem, body.items[0].menu_item_id)
            other = MenuItem(
                category_id=original.category_id,
                name="Independent",
                base_price_minor=1000,
                currency="COP",
                enabled=True,
            )
            s.add(other)
            s.flush()
            s.add(ItemStock(item_id=other.id, remaining=1))
            s.commit()
            second = second.model_copy(
                update={"items": [body.items[0].model_copy(update={"menu_item_id": other.id})]}
            )
        if profile == "different_slot":
            from datetime import datetime

            slots = svc.pickup_slots(BID)["slots"]
            second = second.model_copy(
                update={"requested_pickup_at": datetime.fromisoformat(slots[1]["at"])}
            )
    entered, release = Event(), Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(buy, pg, body, holding(entered, release))
        try:
            assert entered.wait(5)
            other = pool.submit(buy, pg, second)
            try:
                result = other.result(timeout=2)
            except TimeoutError:
                pytest.fail("Independent admission blocked on the held order")
            assert result not in {"ValidationError", "IdempotencyConflictError"}
        finally:
            release.set()
        assert first.result(timeout=5) not in {"ValidationError", "IdempotencyConflictError"}
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 2
        assert s.scalar(select(func.count()).select_from(PaymentIntent)) == 2
        if profile == "different_item":
            assert list(s.scalars(select(ItemStock.remaining))) == [0, 0]


@pytest.mark.parametrize("resource", ["stock", "slot"])
def test_last_resource_waits_then_rejects_without_partial_effects(pg, resource):
    body = make_body(pg, remaining=1) if resource == "stock" else prepare(pg, capacity=1)
    entered, release = Event(), Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(buy, pg, body, holding(entered, release))
        try:
            assert entered.wait(5)
            other = pool.submit(
                buy,
                pg,
                body.model_copy(
                    update={
                        "idempotency_key": "loser",
                        "customer": body.customer.model_copy(update={"phone": "3005550602"}),
                    }
                ),
            )
            wait_blocked(pg)
            assert not other.done()
        finally:
            release.set()
        winner = first.result(timeout=5)
        assert other.result(timeout=5) == "ValidationError"
    assert buy(pg, body) == winner
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1
        assert s.scalar(select(func.count()).select_from(PaymentIntent)) == 1
        if resource == "stock":
            assert s.scalar(select(ItemStock.remaining)) == 0


@pytest.mark.parametrize(
    "change",
    ["sold_out", "stale_finite_count", "untracked_to_finite", "finite_to_untracked", "first_pause"],
)
def test_manager_edit_waits_for_accepted_allocation(pg, change):
    finite = change in {"stale_finite_count", "finite_to_untracked"}
    body = make_body(pg, remaining=2 if finite else None)
    item = body.items[0].menu_item_id
    entered, release = Event(), Event()

    def edit():
        with pg() as s:
            svc = Service(s)
            try:
                if change == "first_pause":
                    svc.save_operations_settings(
                        BID,
                        settings().model_copy(
                            update={"scheduled": False, "ordering_enabled": False}
                        ),
                        principal(),
                    )
                else:
                    stock(
                        svc,
                        item,
                        None if change in {"sold_out", "finite_to_untracked"} else 1,
                        version=1 if finite else 0,
                        sold_out=change == "sold_out",
                    )
                return "saved"
            except IdempotencyConflictError:
                s.rollback()
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(buy, pg, body, holding(entered, release))
        try:
            assert entered.wait(5)
            edit_future = pool.submit(edit)
            wait_blocked(pg)
            assert not edit_future.done()
        finally:
            release.set()
        assert first.result(timeout=5) not in {"ValidationError", "IdempotencyConflictError"}
        assert edit_future.result(timeout=5) == ("stale" if finite else "saved")
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1
        if finite:
            assert s.get(ItemStock, item).remaining == 1
    if change in {"first_pause", "sold_out"}:
        assert (
            buy(pg, body.model_copy(update={"idempotency_key": "after-edit"})) == "ValidationError"
        )


@pytest.mark.parametrize("tracked", [True, False])
def test_stock_mode_edit_committed_first_controls_next_order(pg, tracked):
    body = make_body(pg, remaining=1)
    item = body.items[0].menu_item_id
    with pg() as s:
        stock(Service(s), item, 0 if tracked else None, version=1)
    result = buy(pg, body)
    assert (result == "ValidationError") == tracked
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == (0 if tracked else 1)


@pytest.mark.parametrize("scheduled", [False, True])
def test_mixed_cart_rejection_rolls_back_earlier_stock(pg, scheduled):
    body = prepare(pg, stock=True, capacity=1) if scheduled else make_body(pg, remaining=1)
    with pg() as s:
        original = s.get(MenuItem, body.items[0].menu_item_id)
        other = MenuItem(
            id="zz-unavailable",
            category_id=original.category_id,
            name="No stock",
            base_price_minor=1000,
            currency="COP",
            enabled=True,
        )
        s.add(other)
        s.flush()
        s.add(ItemStock(item_id=other.id, remaining=1))
        s.commit()
        mixed = body.model_copy(
            update={
                "items": [*body.items, body.items[0].model_copy(update={"menu_item_id": other.id})]
            }
        )

    class DepletedAfterQuote(Service):
        def allocate_pickup_and_stock(self, profile, request):
            # Quote succeeds, then a separate committed sale consumes the later item.
            # Prove the earlier decrement actually happened before rejecting the cart.
            with pg() as competitor:
                competitor.get(ItemStock, "zz-unavailable").remaining = 0
                competitor.commit()
            try:
                super().allocate_pickup_and_stock(profile, request)
            except ValidationError:
                self.session.expire_all()
                assert self.session.get(ItemStock, body.items[0].menu_item_id).remaining == 0
                raise
            raise AssertionError("Depleted cart was accepted")

    assert buy(pg, mixed, DepletedAfterQuote) == "ValidationError"
    with pg() as s:
        assert s.get(ItemStock, body.items[0].menu_item_id).remaining == 1
        assert s.scalar(select(func.count()).select_from(Order)) == 0
        assert s.scalar(select(func.count()).select_from(PaymentIntent)) == 0
    # Reuse the rejected key with a valid cart: no stranded key, unit, or pickup slot.
    assert buy(pg, body) not in {"ValidationError", "IdempotencyConflictError"}
    with pg() as s:
        assert s.get(ItemStock, body.items[0].menu_item_id).remaining == 0
        assert s.scalar(select(func.count()).select_from(Order)) == 1


@pytest.mark.parametrize("change", ["sold_out", "zero_stock", "pause"])
def test_manager_change_first_blocks_then_rejects_new_admission(pg, change):
    body = make_body(pg)
    entered, release = Event(), Event()

    class HeldManager(Service):
        def _commit_event(self, **kwargs):
            self.session.flush()
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Manager gate not released")
            return super()._commit_event(**kwargs)

    def edit():
        with pg() as s:
            svc = HeldManager(s)
            if change == "pause":
                svc.save_operations_settings(
                    BID,
                    settings().model_copy(update={"scheduled": False, "ordering_enabled": False}),
                    principal(),
                )
            else:
                stock(
                    svc,
                    body.items[0].menu_item_id,
                    0 if change == "zero_stock" else None,
                    sold_out=change == "sold_out",
                )

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(edit)
        try:
            assert entered.wait(5)
            order = pool.submit(buy, pg, body)
            wait_blocked(pg)
            assert not order.done()
        finally:
            release.set()
        writer.result(timeout=5)
        assert order.result(timeout=5) == "ValidationError"
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 0
        assert s.scalar(select(func.count()).select_from(PaymentIntent)) == 0


def test_lowered_capacity_preserves_accepted_order_and_replay(pg):
    body = prepare(pg, capacity=2)
    original = buy(pg, body)
    with pg() as s:
        svc = Service(s)
        svc.save_operations_settings(
            BID, settings().model_copy(update={"expected_version": 1, "capacity": 1}), principal()
        )
    assert buy(pg, body) == original
    assert buy(pg, body.model_copy(update={"idempotency_key": "no-capacity"})) == "ValidationError"
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 1


def test_cancellation_does_not_automatically_restock_prepared_units(pg):
    # Current conservative contract: a merchant must explicitly recount stock.
    # This is not an implemented expiry/automatic-restocking capability.
    body = make_body(pg, remaining=2)
    original = buy(pg, body)
    with pg() as s:
        svc = Service(s)
        svc.transition_order(original, "cancelled")
        svc.transition_order(original, "cancelled")
        assert s.get(ItemStock, body.items[0].menu_item_id).remaining == 1
        assert s.scalar(select(func.count()).select_from(Order)) == 1


def test_other_business_does_not_wait_for_admission(pg):
    from world_model.restaurant_commerce.models import Menu, MenuCategory, RestaurantCommerceProfile

    body = make_body(pg, remaining=1)
    with pg() as s:
        s.add(
            RestaurantCommerceProfile(
                business_id="synthetic-independent",
                slug="synthetic-independent",
                display_name="Synthetic independent",
                payment_provider="simulated",
                pickup_enabled=True,
            )
        )
        s.flush()
        menu = Menu(business_id="synthetic-independent", name="Synthetic")
        s.add(menu)
        s.flush()
        category = MenuCategory(menu_id=menu.id, name="Synthetic")
        s.add(category)
        s.flush()
        item = MenuItem(
            category_id=category.id,
            name="Independent stock",
            base_price_minor=1000,
            currency="COP",
            enabled=True,
        )
        s.add(item)
        s.flush()
        s.add(ItemStock(item_id=item.id, remaining=1))
        s.commit()
        other = body.model_copy(
            update={
                "idempotency_key": "tenant-b",
                "items": [body.items[0].model_copy(update={"menu_item_id": item.id})],
            }
        )
    entered, release = Event(), Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(buy, pg, body, holding(entered, release))
        try:
            assert entered.wait(5)
            result = pool.submit(buy, pg, other, Service, "synthetic-independent").result(timeout=2)
            assert result not in {"ValidationError", "IdempotencyConflictError"}
        finally:
            release.set()
        first.result(timeout=5)
    with pg() as s:
        assert s.scalar(select(func.count()).select_from(Order)) == 2
        assert all(n == 0 for n in s.scalars(select(ItemStock.remaining)))
