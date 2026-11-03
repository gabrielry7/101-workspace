"""Regression requirements for bounded telemetry and fail-closed release checks."""

from fastapi.testclient import TestClient
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.observability import MetricsRegistry


def test_unmatched_urls_and_methods_have_bounded_metric_cardinality():
    app = create_app(database_url="sqlite://", payment_recovery_enabled=False)
    with TestClient(app) as client:
        for n in range(40):
            assert client.get(f"/private-customer-reference-{n}").status_code == 404
            assert client.request(f"CUSTOM{n}", "/health").status_code == 405
        assert client.get("/health").status_code == 200
    metrics = app.state.metrics.snapshot()
    assert len(metrics["requests_total"]) <= 3
    assert not any("private-customer" in key for key in metrics["requests_total"])
    assert metrics["requests_total"]["GET /health|200"] == 1


def test_metric_registry_defensive_limit_retains_total():
    metrics = MetricsRegistry()
    for n in range(2000):
        metrics.record_request("GET", f"/arbitrary/{n}", 200, 1)
    assert len(metrics.requests_total) <= 257
    assert len(metrics.latency_count) <= 257
    assert sum(metrics.requests_total.values()) == 2000


def test_exception_metrics_use_template_and_record_once():
    app = create_app(database_url="sqlite://", payment_recovery_enabled=False)

    @app.get("/failure/{identifier}")
    def fail(identifier: str):
        raise RuntimeError("synthetic")

    with TestClient(app, raise_server_exceptions=False) as client:
        for n in range(5):
            response = client.get(f"/failure/{n}")
            assert response.status_code == 500
            assert response.json()["detail"] == "Internal server error"
    snapshot = app.state.metrics.snapshot()
    assert snapshot["requests_total"] == {"GET /failure/{identifier}|500": 5}


def test_request_body_deadline_prevents_unbounded_slow_upload():
    import asyncio

    from world_model.restaurant_commerce.security import MaxBodySizeMiddleware

    messages = []
    called = []

    async def downstream(scope, receive, send):
        called.append(True)

    async def stalled():
        await asyncio.sleep(10)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    async def exercise():
        middleware = MaxBodySizeMiddleware(downstream, body_timeout_seconds=0.03)
        await asyncio.wait_for(middleware({"type": "http", "headers": []}, stalled, send), 0.2)

    asyncio.run(exercise())
    assert not called
    assert messages[0]["status"] == 408
    assert (b"connection", b"close") in messages[0]["headers"]


def test_quarantine_rejects_large_recovery_before_json_parser(factory, tmp_path, monkeypatch):
    from starlette.requests import Request
    from test_deployment_m6 import config_file, runtime

    with factory() as session:
        engine = session.get_bind()
    monkeypatch.setattr(runtime, "engine_for", lambda _: engine)
    parsed = []
    actual = Request.json

    async def record(self):
        parsed.append(len(await self.body()))
        return await actual(self)

    monkeypatch.setattr(Request, "json", record)
    with TestClient(runtime.application(runtime.config(config_file(tmp_path)), "test")) as client:
        for path in [
            "/api/restaurants/demo-restaurant-bogota/orders/recover",
            "/invented/orders/recover",
        ]:
            response = client.post(path, content=b'{"payload":"' + b"x" * 2_000_000 + b'"}')
            assert response.status_code in {413, 503}
    assert parsed == []


def test_request_body_deadline_is_total_not_reset_per_chunk():
    import asyncio

    from world_model.restaurant_commerce.security import MaxBodySizeMiddleware

    messages, called = [], []

    async def app(scope, receive, send):
        called.append(True)

    async def drip():
        await asyncio.sleep(0.01)
        return {"type": "http.request", "body": b"x", "more_body": True}

    async def send(message):
        messages.append(message)

    async def exercise():
        middleware = MaxBodySizeMiddleware(app, body_timeout_seconds=0.04)
        await asyncio.wait_for(middleware({"type": "http", "headers": []}, drip, send), 0.3)

    asyncio.run(exercise())
    assert not called
    assert messages[0]["status"] == 408


def test_small_chunked_body_reaches_app_intact_and_disconnect_does_not():
    import asyncio

    from world_model.restaurant_commerce.security import MaxBodySizeMiddleware

    received = []

    async def app(scope, receive, send):
        received.append(await receive())

    async def send(message):
        raise AssertionError("No early rejection expected")

    async def exercise(chunks):
        async def receive():
            return chunks.pop(0)

        await MaxBodySizeMiddleware(app)({"type": "http", "headers": []}, receive, send)

    asyncio.run(
        exercise(
            [
                {"type": "http.request", "body": b"first", "more_body": True},
                {"type": "http.request", "body": b"second", "more_body": False},
            ]
        )
    )
    assert received == [{"type": "http.request", "body": b"firstsecond", "more_body": False}]
    received.clear()
    asyncio.run(exercise([{"type": "http.disconnect"}]))
    assert not received
