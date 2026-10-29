# Independent CLI -> database -> HTTP consumer check against a disposable SQLite file.
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from world_model.restaurant_commerce import staff_admin
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.models import StaffAudit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=pathlib.Path, required=True)
args = parser.parse_args()
root = args.output
root.mkdir(parents=True, exist_ok=True)
start = datetime.datetime.now(datetime.UTC).isoformat()
password = "synthetic CLI lifecycle passphrase"
with tempfile.TemporaryDirectory(prefix="commerce-m4-cli-") as d:
    url = "sqlite:///" + d + "/staff.db"
    app = create_app(database_url=url, seed=True, payment_recovery_enabled=False)

    def command(action, *extra):
        args = [
            "staff_admin",
            action,
            "--username",
            "cli.staff",
            "--actor",
            "local-test-admin",
            *extra,
        ]
        with (
            patch.dict(os.environ, {"COMMERCE_DATABASE_URL": url}),
            patch.object(sys, "argv", args),
            patch("getpass.getpass", return_value=password),
        ):
            staff_admin.main()

    command("create", "--business", "demo-restaurant-bogota", "--role", "manager")
    with TestClient(app) as client:

        def login():
            r = client.post(
                "/api/staff/login",
                json={"username": "cli.staff", "password": password},
                headers={"X-101-Login": "1"},
            )
            assert r.status_code == 200
            return {"X-101-CSRF": client.get("/api/staff/me").json()["csrf"]}

        headers = login()
        command(
            "membership", "--business", "demo-restaurant-bogota", "--role", "viewer"
        )
        assert (
            client.post(
                "/api/operator/restaurants/demo-restaurant-bogota/winback/plan",
                json={"limit": 1},
                headers=headers,
            ).status_code
            == 403
        )
        command("reset-password")
        assert client.get("/api/staff/me").status_code == 401
        headers = login()
        command("remove-membership", "--business", "demo-restaurant-bogota")
        assert (
            client.get(
                "/api/operator/restaurants/demo-restaurant-bogota/orders"
            ).status_code
            == 403
        )
        command("disable")
        assert client.get("/api/staff/me").status_code == 401
    with app.state.session_factory() as session:
        actions = [
            a.action
            for a in session.scalars(
                select(StaffAudit).where(StaffAudit.actor_id == "local-test-admin")
            )
        ]
        assert len(actions) == 5
    app.state.engine.dispose()
receipt = {
    "command": [sys.executable, *sys.argv],
    "revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip(),
    "start": start,
    "end": datetime.datetime.now(datetime.UTC).isoformat(),
    "execution": "COMPLETE",
    "outcome": "PASS",
    "checks": 5,
    "actions": actions,
    "note": "Trusted administrator CLI invoked with synthetic interactive prompt input; real HTTP session issuance and subsequent denial verified. Disposable SQLite cleaned.",
}
(root / "cli-lifecycle.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("CLI lifecycle: 5 checks pass")
