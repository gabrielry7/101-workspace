#!/usr/bin/env python3
"""Execute the built workspace wheel outside the source tree, without provider IO.

Dependencies come from the invoking test environment. This is an application-wheel
qualification, not an offline hash-locked production dependency installation.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

CHILD = r"""
import json, sys
from pathlib import Path
import httpx
from fastapi.testclient import TestClient
import world_model.restaurant_commerce.api as source
from world_model.restaurant_commerce.staff import provision
from world_model.restaurant_commerce.workspace_access import LEGACY_PAGES

assert Path(source.__file__).is_relative_to(Path(sys.argv[1]))


def forbidden(*a, **kw):
    raise AssertionError("Provider HTTP forbidden")


httpx.HTTPTransport.handle_request = forbidden
app = source.create_app(
    database_url="sqlite:///" + sys.argv[2],
    seed=True,
    demo_mode=True,
    payment_recovery_enabled=False,
    provider_recovery_enabled=False,
    social_worker_enabled=False,
)
bid = "demo-restaurant-bogota"
with app.state.session_factory() as s:
    provision(
        s,
        "wheel.manager",
        "synthetic wheel qualification only",
        bid,
        "manager",
        actor="fixture",
    )
with TestClient(app) as c:
    assert c.get("/").status_code == 400
    assert c.get("/?business_id=" + bid).status_code == 200
    assert c.get("/join/" + bid).status_code == 200
    assert c.get("/workspace/sales", follow_redirects=False).status_code == 307
    assert (
        c.post(
            "/api/staff/login",
            headers={"X-101-Login": "1"},
            json={
                "username": "wheel.manager",
                "password": "synthetic wheel qualification only",
            },
        ).status_code
        == 200
    )
    from world_model.restaurant_commerce.checkout_design import CONTRACT
    design_url = "/api/operator/restaurants/" + bid + "/checkout-design"
    assert c.get("/workspace/website").status_code == 200
    assert c.get(design_url).json()["revision"] == 0
    csrf = c.get("/api/staff/me").json()["csrf"]
    changed = c.put(design_url, headers={"X-101-CSRF": csrf}, json={"expected_revision":0,"profile":CONTRACT["presets"]["neutral"]})
    assert changed.status_code == 200, changed.text
    assert c.get("/api/restaurants/" + bid + "/checkout-design").json()["revision"] == 1
    preview = c.get("/?business_id=" + bid + "&checkout_preview=1")
    assert preview.status_code == 200 and preview.headers["X-Frame-Options"] == "SAMEORIGIN"
    for asset in ["checkout-chassis.js","checkout-chassis.css","checkout-contract.js","checkout-anatomy.js","checkout-bones.js","checkout-types.js"]:
        assert c.get("/assets/"+asset).status_code == 200
    redirects = {}
    for old in sorted(LEGACY_PAGES):
        r = c.get(old + "?business_id=" + bid, follow_redirects=False)
        assert r.status_code == 307 and r.headers["location"].startswith("/workspace/")
        dest = c.get(r.headers["location"])
        assert dest.status_code == 200 and "staffUsername" not in dest.text
        redirects[old] = r.headers["location"].split("?")[0]
    assert c.get("/api/operator/restaurants/" + bid + "/connections").status_code == 200
    assert c.get("/api/operator/restaurants/" + bid + "/signup").status_code == 200
    assert c.get("/workspace-assets/assets/101-ui-font.css").status_code == 200
    print(
        json.dumps(
            {
                "app_imported_from_wheel": True,
                "checkout_design_round_trip": True,
                "retired_entries": redirects,
                "missing_business": 400,
                "public_merchant": 200,
                "public_signup": 200,
                "live_provider_calls": 0,
            }
        )
    )
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="workspace-wheel-") as scratch:
        folder = Path(scratch)
        installed = folder / "installed"
        installed.mkdir()
        with zipfile.ZipFile(args.wheel) as wheel:
            for name in wheel.namelist():
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError("Unsafe wheel path")
            wheel.extractall(installed)
        result = subprocess.run(
            [sys.executable, "-c", CHILD, str(installed), str(folder / "fixture.db")],
            cwd=folder,
            env={**os.environ, "PYTHONPATH": str(installed)},
            text=True,
            capture_output=True,
        )
        if result.returncode:
            sys.stderr.write(result.stderr)
            raise SystemExit(result.returncode)
        report = json.loads(result.stdout)
        report.update(
            wheel=args.wheel.name, sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest()
        )
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
