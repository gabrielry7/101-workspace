import asyncio
import json
import time

from timing import Probe, record


def test_probe_keeps_request_context_and_omits_secrets(tmp_path):
    async def app(scope, receive, send):
        await asyncio.to_thread(lambda: record("thread_work", time.perf_counter()))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"secret"})

    async def send(message):
        pass

    asyncio.run(
        Probe(app, tmp_path)(
            {
                "type": "http",
                "method": "POST",
                "path": "/secret",
                "headers": [(b"authorization", b"secret")],
            },
            None,
            send,
        )
    )
    rows = [json.loads(x) for p in tmp_path.glob("*.jsonl") for x in p.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["status"] == 200
    assert rows[0]["spans"][0]["name"] == "thread_work"
    assert rows[0]["total_ms"] >= rows[0]["spans"][0]["duration_ms"] >= 0
    assert "secret" not in json.dumps(rows)


def test_probe_records_failure_and_resets_context(tmp_path):
    from timing import current

    async def app(*args):
        raise RuntimeError("failure")

    async def go():
        try:
            await Probe(app, tmp_path)({"type": "http", "method": "POST"}, None, None)
        except RuntimeError:
            pass
        assert current.get() is None

    asyncio.run(go())
    row = json.loads(next(tmp_path.glob("*.jsonl")).read_text())
    assert row["status"] is None and row["total_ms"] >= 0
