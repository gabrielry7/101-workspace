#!/usr/bin/env python3
"""Build and test the actual local artifact; execute native mandatory security layers.

Private fresh run dir, synthetic PostgreSQL only. No provider credentials/calls.
Missing layers, zero coverage, expired reviews or incomplete scans fail the gate.
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "deployment"), str(ROOT / "scripts"), str(ROOT / "adversarial")]
import commerce_release as release  # noqa: E402
import runtime  # noqa: E402
import scanners  # noqa: E402
from gate import finding, save, verdict  # noqa: E402
from qualify_operations_m6 import Run, port  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--wheelhouse", required=True)
    p.add_argument("--tool-root", required=True)
    p.add_argument("--semgrep", required=True)
    p.add_argument("--rules-dir", required=True)
    p.add_argument("--trivy-cache", required=True)
    p.add_argument("--layers", default="tests,static,zap")
    p.add_argument("--test-timeout-seconds", type=int, default=1800,
                   help="Bounded full-suite wall-clock allowance (60–3600 seconds)")
    a = p.parse_args()
    if not 60 <= a.test_timeout_seconds <= 3600:
        p.error("--test-timeout-seconds must be between 60 and 3600")
    run = Run(a.run_dir)
    layers, findings = {}, []
    scanners.TOOLCHAIN = Path(a.tool_root).resolve()
    cluster, site = run.path / "postgres", run.path / "site"
    pgport, webport = port(), port()
    pgctl = ["pg_ctl", "-D", str(cluster), "-l", str(run.path / "postgres.log"), "-w"]
    started_pg = False
    engine = client = None
    gate = {"execution": "PARTIAL", "outcome": "FAIL"}
    spec = {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_path": str(ROOT),
        "trivy_cache": a.trivy_cache,
    }

    def source_inventory():
        paths = [
            p
            for folder in [
                "src",
                "deployment",
                "scripts",
                "adversarial",
                "security",
                "tests",
                "sandbox_receiver",
            ]
            for p in (ROOT / folder).rglob("*")
            if p.is_file()
            and p.suffix
            in {
                ".py",
                ".js",
                ".mjs",
                ".json",
                ".yaml",
                ".html",
                ".css",
                ".txt",
                ".lock",
                ".toml",
                ".yml",
                ".ts",
            }
            and not any(x in p.parts for x in ["node_modules", "__pycache__", ".pytest_cache"])
            and not any(part.endswith(".egg-info") for part in p.parts)
        ]
        paths.append(ROOT / "pyproject.toml")
        paths.extend((ROOT.parents[1] / ".github/workflows").glob("commerce-security.yml"))
        return {os.path.relpath(p, ROOT): release.digest(p) for p in paths}

    initial_source = source_inventory()
    save(run.evidence / "source-sha256.json", initial_source)
    try:
        rules = json.loads((ROOT / "security/rules.lock.json").read_text())
        version = run.command("semgrep-version", [a.semgrep, "--version"]).strip()
        assert version == rules["semgrep_version"], "Unexpected Semgrep version"
        paths = []
        for pack in rules["packs"]:
            path = Path(a.rules_dir) / (pack["name"] + ".yaml")
            assert release.digest(path) == pack["sha256"], "Security rule hash mismatch"
            paths.append(str(path.resolve()))
        spec.update(semgrep_rules=paths, semgrep_binary=str(Path(a.semgrep).resolve()))
        run.command(
            "build",
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                run.path / "wheel",
                ROOT,
            ],
        )
        wheel = next((run.path / "wheel").glob("*.whl"))
        spec["wheel_sha256"] = release.digest(wheel)
        bundle = run.path / "bundle"
        digest = release.pack(wheel, a.wheelhouse, bundle, spec["revision"])
        rid = release.install(bundle, digest, site)
        target = site / "releases" / rid
        spec["python"] = str(target / "venv/bin/python")
        installed = next((target / "venv/lib").glob("python*/site-packages"))
        sys.path.insert(0, str(installed))
        importlib.invalidate_caches()
        import httpx
        import world_model.restaurant_commerce.api as app_module
        from world_model.restaurant_commerce import staff
        from world_model.restaurant_commerce.db import init_schema, session_factory
        from world_model.restaurant_commerce.models import RestaurantCommerceProfile
        from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
        from world_model.restaurant_commerce.seed import seed_demo

        assert Path(app_module.__file__).is_relative_to(installed)
        package = {
            str(f.relative_to(ROOT / "src")): release.digest(f)
            for f in (ROOT / "src/world_model/restaurant_commerce").rglob("*")
            if f.is_file() and "__pycache__" not in f.parts
        }
        assert all(release.digest(installed / path) == sha for path, sha in package.items())
        save(
            run.evidence / "artifact.json",
            {
                **spec,
                "manifest_sha256": digest,
                "release": rid,
                "source_dirty": bool(
                    subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
                ),
                "package_sha256": package,
            },
        )
        run.command("initdb", ["initdb", "-D", cluster, "-A", "trust", "--no-locale", "-E", "UTF8"])
        with (cluster / "postgresql.conf").open("a") as f:
            f.write(
                f"\nlisten_addresses='127.0.0.1'\nport={pgport}\nunix_socket_directories=''\nmax_connections=50\nshared_buffers='16MB'\n"
            )
        run.command("postgres-start", [*pgctl, "start"])
        started_pg = True
        run.command("createdb", ["createdb", "-h", "127.0.0.1", "-p", pgport, "m6b"])
        cfg = {
            "mode": "rehearsal",
            "database_url": f"postgresql+psycopg://{os.environ['USER']}@127.0.0.1:{pgport}/m6b",
            "state_dir": str(run.path / "state"),
            "public_access_secret": "synthetic-only-m6b-recovery-signing-secret",
            "allow_writes": True,
        }
        config_path = run.path / "runtime.json"
        runtime.write_json(config_path, cfg)
        cfg = runtime.config(config_path)
        engine = runtime.engine_for(cfg)
        init_schema(engine)
        sessions = session_factory(engine)
        password = "synthetic M6b scoped staff passphrase"
        with sessions() as s:
            seed_demo(s)
            s.add(
                RestaurantCommerceProfile(
                    business_id="other", slug="other", display_name="Other synthetic"
                )
            )
            s.commit()
            for business in [BID, "other"]:
                staff.provision(
                    s, "m6b." + business, password, business, "manager", actor="local-qualification"
                )
        release.activate(site, rid, config_path, webport)
        spec.update(base_url=f"http://127.0.0.1:{webport}", business_ids=[BID, "other"])
        client = httpx.Client(base_url=spec["base_url"], trust_env=False, timeout=15)
        checks = []

        def check(name, expression):
            assert expression, name
            checks.append(name)

        check("artifact identity", client.get("/deployment").json()["release"] == rid)
        check("ready", client.get("/ready").status_code == 200)
        store = client.get(f"/api/restaurants/{BID}/storefront").json()
        item = next(
            i
            for m in store["menus"]
            for c in m["categories"]
            for i in c["items"]
            if not i["modifier_groups"]
        )
        body = {
            "customer": {"name": "Synthetic security", "phone": "3005550601"},
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "idempotency_key": "baseline",
            "recovery_secret": "a" * 64,
        }
        first = client.post(f"/api/restaurants/{BID}/orders", json=body)
        check("successful checkout", first.status_code == 200)
        order = first.json()
        check(
            "same-order replay",
            client.post(f"/api/restaurants/{BID}/orders", json=body).json()["id"] == order["id"],
        )
        check("anonymous order denied", client.get("/api/orders/" + order["id"]).status_code == 401)
        check(
            "customer capability succeeds",
            client.get(
                "/api/orders/" + order["id"], headers={"X-101-Order-Token": order["access_token"]}
            ).status_code
            == 200,
        )
        check(
            "customer wrong capability denied",
            client.get(
                "/api/orders/" + order["id"], headers={"X-101-Order-Token": "invalid"}
            ).status_code
            == 401,
        )
        check(
            "staff login",
            client.post(
                "/api/staff/login",
                headers={"X-101-Login": "1"},
                json={"username": "m6b." + BID, "password": password},
            ).status_code
            == 200,
        )
        me = client.get("/api/staff/me").json()
        spec["single_staff_headers"] = {
            "Cookie": "commerce_staff=" + client.cookies.get("commerce_staff"),
            "X-101-CSRF": me["csrf"],
        }
        check(
            "own business allowed",
            client.get(f"/api/operator/restaurants/{BID}/orders").status_code == 200,
        )
        check(
            "other business denied",
            client.get("/api/operator/restaurants/other/orders").status_code == 403,
        )
        check("csrf required", client.post("/api/staff/logout").status_code == 403)
        layers["baseline"] = {
            "execution": "COMPLETE",
            "outcome": "PASS",
            "checks": len(checks),
            "names": checks,
        }
        runtime.write_json(run.path / "private-scanner-config.json", spec)
        save(run.evidence / "layers.json", layers)
        if "tests" in a.layers.split(","):
            try:
                env = {
                    **os.environ,
                    "PYTHONPATH": os.pathsep.join([str(installed), str(ROOT / "security")]),
                    "COMMERCE_QUALIFICATION_PROOF": str(run.evidence / "pytest-proof.json"),
                    "COMMERCE_EXPECTED_SITE": str(installed),
                    "COMMERCE_PAYMENT_TEST_DATABASE_URL": cfg["database_url"],
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "COMMERCE_M5_ARTIFACTS": str(run.path / "private-browser"),
                    "COMMERCE_BROWSER_ARTIFACTS": str(run.path / "private-browser"),
                }
                run.command(
                    "tests",
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "pytest",
                        "-p",
                        "qualification_plugin",
                        "-q",
                        "tests",
                        "--junitxml=" + str(run.evidence / "tests.xml"),
                    ],
                    env=env,
                    timeout=a.test_timeout_seconds,
                )
            except Exception as exc:
                layers["tests"] = {
                    "execution": "PARTIAL",
                    "outcome": "ERROR",
                    "error_class": type(exc).__name__,
                }
            if (run.evidence / "tests.xml").exists():
                import defusedxml.ElementTree as ET

                suite = ET.parse(run.evidence / "tests.xml").getroot().find("testsuite")
                native = next((r for r in run.commands if r["name"] == "tests"), {})
                proof = (
                    json.loads((run.evidence / "pytest-proof.json").read_text())
                    if (run.evidence / "pytest-proof.json").exists()
                    else {}
                )
                layers["tests"] = {
                    "execution": "COMPLETE" if native.get("exit_code") == 0 else "PARTIAL",
                    "native_exit_code": native.get("exit_code"),
                    "postgres_count": len(proof.get("postgres_test_ids", [])),
                    "outcome": "PASS"
                    if int(suite.get("failures")) + int(suite.get("errors")) == 0
                    else "FAIL",
                    "count": int(suite.get("tests")),
                    "executed_modules": sorted(
                        {c.get("classname", "").split(".")[-1] for c in suite.findall("testcase")}
                    ),
                    "failures": int(suite.get("failures")),
                    "errors": int(suite.get("errors")),
                    "skipped": int(suite.get("skipped")),
                    "browser_count": sum(
                        "browser" in c.get("classname", "")
                        or "frontend_m5" in c.get("classname", "")
                        for c in suite.findall("testcase")
                    ),
                    "postgres_fixtures": proof.get("installed_artifact") is True
                    and bool(proof.get("postgres_test_ids")),
                }
        if "static" in a.layers.split(","):
            rec = scanners.Recorder(run.evidence / "static", spec)
            try:
                layers["semgrep"] = scanners.semgrep(rec, ROOT)
                native = json.loads((rec.output / "semgrep.json").read_text())
                for f in native.get("results", []):
                    path = Path(f["path"])
                    path = path if path.is_absolute() else ROOT / path
                    source = path.read_bytes()
                    snippet = source[f["start"]["offset"] : f["end"]["offset"]].decode()
                    findings.append(
                        finding(
                            f["check_id"],
                            str(path.relative_to(ROOT)),
                            source.decode() + "\nMATCH:\n" + snippet,
                            f["extra"]["severity"],
                        )
                    )
            except Exception as exc:
                layers["semgrep"] = {
                    "execution": "PARTIAL",
                    "outcome": "ERROR",
                    "error_class": type(exc).__name__,
                }
            try:
                scans = scanners.trivy(rec, ROOT, spec)
                source = json.loads((rec.output / "trivy-source.json").read_text())
                sr = scans["source"]
                sr["config_targets"] = sum(
                    bool(x.get("MisconfSummary")) or x.get("Class") == "config"
                    for x in source.get("Results", [])
                )
                sr["source_files"] = sum(f.is_file() for f in ROOT.rglob("*.py"))
                layers["secrets_config"] = sr
                dep = json.loads((rec.output / "trivy-dependencies.json").read_text())
                inv = {
                    line.split("==")[0].lower().replace("_", "-"): line.split("==")[1]
                    for line in (rec.output / "runtime-pip-freeze.log").read_text().splitlines()
                    if "==" in line
                }
                found = {
                    x["Name"].lower().replace("_", "-"): x["Version"]
                    for r in dep.get("Results", [])
                    for x in r.get("Packages", [])
                }
                dr = scans["dependencies"]
                dr["installed_inventory_match"] = bool(inv) and all(
                    found.get(k) == v for k, v in inv.items()
                )
                dr["database_updated_at"] = json.loads(
                    (Path(a.trivy_cache) / "db/metadata.json").read_text()
                )["UpdatedAt"]
                layers["dependencies"] = dr
                layers["container"] = {
                    "execution": "NOT_APPLICABLE",
                    "outcome": "UNASSESSED",
                    "reason": (
                        "Selected deployment artifact is a venv, not a built OCI image; "
                        "optional legacy container remains unqualified"
                    ),
                }
                for report in [source, dep]:
                    for target_result in report.get("Results", []):
                        for key in ["Vulnerabilities", "Secrets", "Misconfigurations"]:
                            for f in target_result.get(key, []) or []:
                                if f.get("Status") == "PASS":
                                    continue
                                identifier = (
                                    f.get("VulnerabilityID") or f.get("RuleID") or f.get("ID")
                                )
                                evidence = json.dumps(f, sort_keys=True)
                                findings.append(
                                    finding(
                                        identifier,
                                        target_result["Target"],
                                        evidence,
                                        f.get("Severity", "UNKNOWN"),
                                        "dependencies" if report is dep else "secrets_config",
                                    )
                                )
            except Exception as exc:
                layers["dependencies"] = {
                    "execution": "PARTIAL",
                    "outcome": "ERROR",
                    "error_class": type(exc).__name__,
                }
            save(run.evidence / "layers.json", layers)
            save(run.evidence / "findings.json", findings)
        if "zap" in a.layers.split(","):
            rec = scanners.Recorder(run.path / "private-zap", spec)
            try:
                layers["zap"] = scanners.zap_scan(rec, spec)
                native = json.loads((rec.output / "zap-alerts.json").read_text())
                for f in native.get("alerts", []):
                    evidence = json.dumps(
                        {
                            k: f.get(k)
                            for k in ["alertRef", "name", "risk", "confidence", "param", "evidence"]
                        },
                        sort_keys=True,
                    )
                    findings.append(
                        finding(
                            f.get("alertRef", f["pluginId"]),
                            f["url"].replace(spec["base_url"], ""),
                            evidence,
                            f["risk"].upper(),
                            "zap",
                        )
                    )
            except Exception as exc:
                layers["zap"] = {
                    "execution": "PARTIAL",
                    "outcome": "ERROR",
                    "error_class": type(exc).__name__,
                }
            # Only redacted reports go to shareable evidence; raw session DB stays private.
            dest = run.evidence / "zap"
            dest.mkdir()
            secrets = [*spec["single_staff_headers"].values(), order["access_token"]]
            for file in rec.output.glob("*.json"):
                save(
                    dest / file.name, scanners.redact_native(json.loads(file.read_text()), secrets)
                )
        for name in ["semgrep", "secrets_config", "dependencies", "zap"]:
            if name in layers:
                layers[name]["finding_count"] = sum(f["layer"] == name for f in findings)
        reviews = json.loads((ROOT / "security/reviews.json").read_text())["reviews"]
        layers["source_integrity"] = {
            "execution": "COMPLETE",
            "outcome": "PASS" if source_inventory() == initial_source else "FAIL",
        }
        gate = verdict(layers, findings, reviews)
    except Exception as exc:
        import traceback

        (run.path / "private-error.txt").write_text(traceback.format_exc())
        gate = {"execution": "PARTIAL", "outcome": "FAIL", "blocker": type(exc).__name__}
    finally:
        if client:
            client.close()
        if engine:
            engine.dispose()
        cleanup = []
        if (site / "active.json").exists():
            try:
                release.stop(site)
                cleanup.append("owned API/worker/monitor stopped")
            except Exception:
                gate["outcome"] = "FAIL"
                cleanup.append("process cleanup failed")
        if started_pg:
            try:
                run.command("postgres-stop", [*pgctl, "-m", "fast", "stop"])
                cleanup.append("owned PostgreSQL stopped")
            except Exception:
                gate["outcome"] = "FAIL"
                cleanup.append("PostgreSQL cleanup failed")
        save(run.evidence / "layers.json", layers)
        save(run.evidence / "findings.json", findings)
        gate.update(
            ended_at=datetime.now(UTC).isoformat(),
            cleanup=cleanup,
            revision=spec["revision"],
            wheel_sha256=spec.get("wheel_sha256"),
            optional_blockers={
                "strix": "No model spending authorization; not run",
                "remote_ci": "Workflow execution/branch protection not established by a local run",
            },
        )
        save(run.evidence / "gate.json", gate)
        print(json.dumps(gate, indent=2))
    return 0 if gate["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
