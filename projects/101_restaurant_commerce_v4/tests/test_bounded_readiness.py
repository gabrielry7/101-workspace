"""P02/P03 deadlines, shared work, schema freshness and event-loop liveness."""

import asyncio
import threading
import time

import anyio
import httpx
import pytest
from sqlalchemy import event, text
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import database_ready
from world_model.restaurant_commerce.readiness import ReadinessProbe


def test_probe_coalesces_bursts_times_out_and_discards_late_success():
    release = threading.Event()
    calls = []

    def check(deadline):
        calls.append(deadline)
        release.wait(2)
        return True

    probe = ReadinessProbe(check, timeout=0.05)

    async def scenario():
        started = time.monotonic()
        assert not any(await asyncio.gather(*(probe.ready() for _ in range(60))))
        assert time.monotonic() - started < 0.5
        assert len(calls) == 1
        assert not any(await asyncio.gather(*(probe.ready() for _ in range(60))))
        assert len(calls) == 1
        release.set()
        while not probe._flight[0].done():
            await asyncio.sleep(0.005)
        # Late true result is discarded; a fresh probe must run.
        assert await probe.ready()
        assert len(calls) == 2
        probe.close()
        assert not await probe.ready()

    try:
        asyncio.run(scenario())
    finally:
        release.set()


def test_probe_error_and_cancelled_waiter_do_not_poison_recovery():
    release = threading.Event()
    calls = []

    def check(_deadline):
        calls.append(1)
        release.wait(2)
        return True

    probe = ReadinessProbe(check)

    async def scenario():
        waiter = asyncio.create_task(probe.ready())
        await asyncio.sleep(0.02)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        second = asyncio.create_task(probe.ready())
        await asyncio.sleep(0.01)
        release.set()
        assert await second
        assert len(calls) == 1
        bad = ReadinessProbe(lambda _: 1 / 0)
        assert not await bad.ready()

    try:
        asyncio.run(scenario())
    finally:
        release.set()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        ReadinessProbe(lambda _: True, timeout=timeout)


def test_http_health_and_readiness_do_not_wait_for_shared_thread_pool(factory):
    engine = factory.kw["bind"]
    app = create_app(engine=engine, payment_recovery_enabled=False)

    async def scenario():
        limiter = anyio.to_thread.current_default_thread_limiter()
        old = limiter.total_tokens
        limiter.total_tokens = 1
        occupied = threading.Event()
        release = threading.Event()

        def hold():
            occupied.set()
            release.wait(3)

        job = asyncio.create_task(anyio.to_thread.run_sync(hold))
        try:
            while not occupied.is_set():
                await asyncio.sleep(0.005)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                start = time.monotonic()
                assert (await client.get("/health")).status_code == 200
                assert time.monotonic() - start < 0.25
                response = await client.get("/ready")
                assert response.status_code == 200
                assert response.headers["cache-control"] == "no-store"
        finally:
            release.set()
            await job
            limiter.total_tokens = old

    asyncio.run(scenario())


def test_readiness_never_caches_schema_success(factory):
    engine = factory.kw["bind"]
    app = create_app(engine=engine, payment_recovery_enabled=False)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/ready")).status_code == 200
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE restaurant_orders RENAME TO missing_orders"))
            try:
                response = await client.get("/ready")
                assert response.status_code == 503
                assert response.headers["cache-control"] == "no-store"
                assert (await client.get("/health")).status_code == 200
            finally:
                with engine.begin() as connection:
                    connection.execute(
                        text("ALTER TABLE missing_orders RENAME TO restaurant_orders")
                    )
            assert (await client.get("/ready")).status_code == 200

    asyncio.run(scenario())


def test_expired_probe_does_not_execute_queries(factory):
    engine = factory.kw["bind"]
    statements = []

    def observe(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        assert not database_ready(engine, deadline=time.monotonic() - 1)
        assert statements == []
    finally:
        event.remove(engine, "before_cursor_execute", observe)


def test_postgres_probe_timeout_does_not_leak_into_checkout_connection(factory):
    engine = factory.kw["bind"]
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL transaction-local settings")
    with engine.connect() as conn:
        before = conn.scalar(text("SHOW statement_timeout"))
    assert database_ready(engine, deadline=time.monotonic() + 1)
    with engine.connect() as conn:
        assert conn.scalar(text("SHOW statement_timeout")) == before


def test_actual_pool_exhaustion_is_bounded_and_recovers(factory):
    from sqlalchemy import create_engine
    from sqlalchemy.pool import QueuePool

    engine = create_engine(
        factory.kw["bind"].url, poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=2
    )
    held = engine.connect()
    probe = ReadinessProbe(
        lambda deadline: database_ready(engine, require_schema=False, deadline=deadline),
        timeout=0.05,
    )

    async def scenario():
        started = time.monotonic()
        assert not await probe.ready()
        assert time.monotonic() - started < 0.5
        held.close()
        while not probe._flight[0].done():
            await asyncio.sleep(0.005)
        assert await probe.ready()

    try:
        asyncio.run(scenario())
    finally:
        held.close()
        engine.dispose()


def test_postgres_statement_execution_is_cancelled(factory):
    engine = factory.kw["bind"]
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL statement timeout")

    def sleep_query(_conn, _cursor, statement, params, _ctx, _many):
        if statement == "SELECT 1":
            return "SELECT pg_sleep(5)", params
        return statement, params

    event.listen(engine, "before_cursor_execute", sleep_query, retval=True)
    try:
        started = time.monotonic()
        assert not database_ready(engine, deadline=started + 0.2)
        assert time.monotonic() - started < 1
    finally:
        event.remove(engine, "before_cursor_execute", sleep_query)
    assert database_ready(engine)


def test_thread_resource_exhaustion_fails_closed(monkeypatch):
    def unavailable(_self):
        raise RuntimeError("cannot start new thread")

    with monkeypatch.context() as patch:
        patch.setattr(threading.Thread, "start", unavailable)
        probe = ReadinessProbe(lambda _: True)
        assert not asyncio.run(probe.ready())
    assert asyncio.run(probe.ready())
