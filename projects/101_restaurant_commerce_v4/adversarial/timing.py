"""Opt-in disposable timing probe. No SQL text, parameters, bodies or auth recorded."""

import contextvars
import functools
import json
import os
import time
import uuid
from pathlib import Path

current = contextvars.ContextVar("commerce_timing", default=None)


def record(name, start):
    row = current.get()
    if row is not None:
        row["spans"].append(
            {
                "name": name,
                "offset_ms": (start - row["_start"]) * 1000,
                "duration_ms": (time.perf_counter() - start) * 1000,
            }
        )


def timed(name, fn):
    @functools.wraps(fn)
    def call(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            record(name, start)

    return call


def install(app, output):
    import fastapi.routing
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from world_model.restaurant_commerce.reliability import ProviderExecutor

    # Acquisition includes new connection establishment; it is NOT pure queue wait.
    pool = app.state.engine.pool
    pool._do_get = timed("connection_acquire", pool._do_get)
    Session.commit = timed("commit_including_flush", Session.commit)
    ProviderExecutor.call = timed("provider_executor", ProviderExecutor.call)

    @event.listens_for(app.state.engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._probe_start = time.perf_counter()

    @event.listens_for(app.state.engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        record("sql_execute", context._probe_start)

    @event.listens_for(app.state.engine, "handle_error")
    def error(context):
        ctx = context.execution_context
        if ctx is not None and hasattr(ctx, "_probe_start"):
            record("sql_error", ctx._probe_start)

    original = fastapi.routing.run_in_threadpool

    async def dispatch(fn, *args, **kwargs):
        queued = time.perf_counter()

        def entered():
            record("endpoint_dispatch_wait", queued)
            return timed("endpoint", fn)(*args, **kwargs)

        return await original(entered)

    fastapi.routing.run_in_threadpool = dispatch
    return Probe(app, output)


class Probe:
    def __init__(self, app, output):
        self.app = app
        self.path = Path(output) / f"requests-{os.getpid()}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start = time.perf_counter()
        row = {
            "id": uuid.uuid4().hex,
            "utc_ns": time.time_ns(),
            "_start": start,
            "pid": os.getpid(),
            "method": scope["method"],
            "spans": [],
            "status": None,
        }
        token = current.set(row)

        async def sent(message):
            if message["type"] == "http.response.start":
                row["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, sent)
        finally:
            row["total_ms"] = (time.perf_counter() - start) * 1000
            route = scope.get("route")
            row["route"] = getattr(route, "path", "<unmatched>")
            del row["_start"]
            current.reset(token)
            # One append per request, separate PID files; overhead assessed by controls.
            with self.path.open("a") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
