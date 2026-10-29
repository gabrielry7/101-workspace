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
    assert mode in {"normal", "paid", "hold_after_success", "delay"}
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
        s.execute(
            "INSERT INTO records VALUES (?,?)", ("delivery:" + kind, json.dumps(body))
        )
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
