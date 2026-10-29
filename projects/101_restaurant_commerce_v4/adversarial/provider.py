"""Inspectable synthetic provider ledger; no outbound network capability used."""

import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI

c = json.loads(Path(os.environ["COMMERCE_TEST_CONFIG"]).read_text())
db = Path(c["run_dir"]) / "provider.sqlite"
app = FastAPI()
with sqlite3.connect(db) as s:
    s.execute(
        "CREATE TABLE IF NOT EXISTS effects (key TEXT PRIMARY KEY, order_id TEXT, body TEXT, response TEXT, calls INTEGER DEFAULT 1)"
    )
    s.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, body TEXT)")
    s.execute("CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY, mode TEXT)")
    s.execute("INSERT OR IGNORE INTO control VALUES (1,'normal')")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/control")
def control(body: dict):
    mode = body.get("mode", "normal")
    assert mode in {"normal", "paid", "hold_after_success", "delay", "refund_delay"}
    with sqlite3.connect(db) as s:
        s.execute("UPDATE control SET mode=? WHERE id=1", (mode,))
    return {"mode": mode}


@app.post("/checkouts")
def checkout(body: dict):
    with sqlite3.connect(db, timeout=15) as s:
        mode = s.execute("SELECT mode FROM control WHERE id=1").fetchone()[0]
        response = {
            "provider": "simulated",
            "provider_reference": "sim_" + body["order_id"],
            "amount_minor": body["amount_minor"],
            "currency": body["currency"],
            "status": "paid" if mode in {"paid", "hold_after_success"} else "pending",
            "checkout_url": "/demo/pay/sim_" + body["order_id"],
            "order_may_proceed": False,
        }
        key = body["idempotency_key"]
        s.execute(
            "INSERT OR IGNORE INTO effects(key,order_id,body,response) VALUES (?,?,?,?)",
            (key, body["order_id"], json.dumps(body), json.dumps(response)),
        )
        row = s.execute("SELECT response FROM effects WHERE key=?", (key,)).fetchone()
        s.execute("UPDATE effects SET calls=calls+1 WHERE key=?", (key,))
    if mode == "delay":
        time.sleep(6)
    if mode == "hold_after_success":
        for _ in range(300):
            with sqlite3.connect(db) as s:
                mode = s.execute("SELECT mode FROM control WHERE id=1").fetchone()[0]
            if mode != "hold_after_success":
                break
            time.sleep(0.1)
    return json.loads(row[0])


@app.post("/events")
def events(body: dict):
    with sqlite3.connect(db) as s:
        s.execute("INSERT INTO records VALUES (?,?)", ("event", json.dumps(body)))
    return {"received": True}


@app.post("/delivery/{kind}")
def delivery(kind: str, body: dict):
    with sqlite3.connect(db) as s:
        s.execute("INSERT INTO records VALUES (?,?)", ("delivery:" + kind, json.dumps(body)))
    return {"received": True}


@app.get("/records")
def records():
    with sqlite3.connect(db) as s:
        effects = [
            {
                "key": r[0],
                "order_id": r[1],
                "response": json.loads(r[2]),
                "calls": r[3] - 1,
            }
            for r in s.execute("SELECT key,order_id,response,calls FROM effects")
        ]
        events = [
            {"kind": r[0], "body": json.loads(r[1])}
            for r in s.execute("SELECT kind,body FROM records")
        ]
    return {
        "effects": effects,
        "records": events,
        "messaging_adapter": "absent in application; no send claimed",
    }


# Independent provider-side refund ledger: never inferred from local app status.
with sqlite3.connect(db) as s:
    s.execute(
        "CREATE TABLE IF NOT EXISTS refunds (key TEXT PRIMARY KEY, order_id TEXT, response TEXT)"
    )


@app.post("/financial/lookup-payment")
def financial_lookup(body: dict):
    with sqlite3.connect(db) as s:
        row = s.execute(
            "SELECT order_id,response FROM effects WHERE key=?", (body["idempotency_key"],)
        ).fetchone()
    if not row:
        return None
    value = json.loads(row[1])
    return dict(
        order_id=row[0],
        provider_reference=value["provider_reference"],
        amount_minor=value["amount_minor"],
        currency=value["currency"],
        status=value["status"],
        evidence_id="provider-lookup:" + row[0],
    )


@app.post("/financial/lookup-refund")
def financial_lookup_refund(body: dict):
    with sqlite3.connect(db) as s:
        row = s.execute(
            "SELECT response FROM refunds WHERE key=?", (body["idempotency_key"],)
        ).fetchone()
    return json.loads(row[0]) if row else None


@app.post("/financial/refund")
def financial_refund(body: dict):
    from fastapi import HTTPException

    with sqlite3.connect(db) as s:
        s.execute("BEGIN IMMEDIATE")
        prior = s.execute(
            "SELECT response FROM refunds WHERE key=?", (body["idempotency_key"],)
        ).fetchone()
        if prior:
            return json.loads(prior[0])
        row = s.execute(
            "SELECT key,response FROM effects WHERE order_id=?", (body["order_id"],)
        ).fetchone()
        if not row:
            raise HTTPException(409, "Unknown provider payment")
        payment = json.loads(row[1])
        if payment["status"] != "paid" or any(
            payment[k] != body[k] for k in ["provider_reference", "amount_minor", "currency"]
        ):
            raise HTTPException(409, "Provider settlement does not match refund request")
        result = {
            k: body[k] for k in ["order_id", "provider_reference", "amount_minor", "currency"]
        }
        result.update(
            status="succeeded",
            evidence_id="refund-evidence:" + body["idempotency_key"],
            refund_reference="rf:" + body["idempotency_key"],
        )
        s.execute(
            "INSERT INTO refunds VALUES (?,?,?)",
            (body["idempotency_key"], body["order_id"], json.dumps(result)),
        )
        payment["status"] = "refunded"
        s.execute("UPDATE effects SET response=? WHERE key=?", (json.dumps(payment), row[0]))
        mode = s.execute("SELECT mode FROM control WHERE id=1").fetchone()[0]
    if mode == "refund_delay":
        time.sleep(6)
    return result


@app.get("/financial/records")
def financial_records():
    with sqlite3.connect(db) as s:
        return [
            dict(key=r[0], order_id=r[1], response=json.loads(r[2]))
            for r in s.execute("SELECT key,order_id,response FROM refunds")
        ]
