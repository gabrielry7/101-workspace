"""Rebuild and execute S01/S02 on an owned PostgreSQL deployment; no remote calls."""

import argparse
import json
import os
import sys
from pathlib import Path

import scanners
from fixture_state import business_inputs
from run import PYTHON, baseline_journey, cleanup, command, now, setup, stop, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scanner-tools", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    started = now()
    c = setup(args.output)
    result = {
        "start": started,
        "revision": c["revision"],
        "wheel_sha256": c["wheel_sha256"],
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
        "layers": {},
    }
    try:
        baseline_journey(c)
        # Quiesce only the owned recovery worker for before/after DB assertions.
        # Request financial operations still use the real controlled provider.
        stop(c, "recovery")
        write(args.output / "config.json", c)
        env = dict(
            os.environ,
            PYTHONPATH=c["installed"],
            COMMERCE_PAYMENT_TEST_DATABASE_URL=c["database_url"],
        )
        code = command(
            c,
            "regressions",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "tests/test_scanner_contract.py",
                "tests/test_campaign_preview_security.py",
                "tests/test_zap_alert_review.py",
                "tests/test_release_gate_m6b.py",
                "tests/test_staff_m4.py",
                "tests/test_financial_resolution_m3b.py",
                "tests/test_campaigns.py",
                "--junitxml=" + str(args.output / "regressions.xml"),
            ],
            timeout=300,
            env=env,
        )
        result["layers"]["regressions"] = {
            "execution": "COMPLETE" if code == 0 else "PARTIAL",
            "outcome": "PASS" if code == 0 else "FAIL",
            "exit_code": code,
        }
        browser_env = dict(env, COMMERCE_RECORD_CONFIG=str(args.output / "config.json"))
        browser_env["PYTHONPATH"] += os.pathsep + str(Path(__file__).parent)
        code = command(
            c,
            "browser-security",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "adversarial/security_browser.py",
                "--junitxml=" + str(args.output / "browser-security.xml"),
            ],
            timeout=90,
            env=browser_env,
        )
        result["layers"]["browser"] = {
            "execution": "COMPLETE" if code == 0 else "PARTIAL",
            "outcome": "PASS" if code == 0 else "FAIL",
        }
        from security_authorization import verify

        with business_inputs(c, args.output / "config.json"):
            fuzz_output = args.output / "fuzz"
            code = command(
                c,
                "api-fuzz",
                [
                    PYTHON,
                    "adversarial/fuzz.py",
                    "--config",
                    args.output / "config.json",
                    "--output",
                    fuzz_output,
                ],
                timeout=600,
                env=browser_env,
            )
            broad_path = fuzz_output / "summary.json"
            broad = json.loads(broad_path.read_text()) if broad_path.exists() else []
            record_path = fuzz_output / "real-records/summary.json"
            records = (
                json.loads(record_path.read_text())
                if record_path.exists()
                else {"execution": "BLOCKED", "outcome": "UNASSESSED"}
            )
            complete = (
                code == 0
                and len(broad) == 3
                and all(
                    x["execution"] == "COMPLETE" and x["outcome"] == "PASS"
                    for x in [*broad, records]
                )
            )
            result["layers"]["api_fuzz"] = {
                "execution": "COMPLETE" if complete else "PARTIAL",
                "outcome": "PASS" if complete else "FAIL",
                "exit_code": code,
                "broad": broad,
                "records": records,
            }
            result["layers"]["authorization"] = verify(c, args.output / "authorization.json")
        scanners.TOOLCHAIN = args.scanner_tools
        rec = scanners.Recorder(args.output / "private-zap", c)
        with business_inputs(c, args.output / "config.json"):
            zap = scanners.zap_scan(rec, c)
        write(rec.output / "result.json", zap)
        # Native informational alerts remain visible. High/medium/low alerts fail this slice.
        alerts = (
            json.loads((rec.output / "zap-alerts.json").read_text()).get("alerts", [])
            if (rec.output / "zap-alerts.json").exists()
            else []
        )
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "security"))
        from alert_review import reviewed_alerts

        review = reviewed_alerts(alerts, c["base_url"], Path(__file__).resolve().parents[1])
        write(args.output / "zap-review.json", review)
        zap["slice_outcome"] = (
            "PASS" if zap["execution"] == "COMPLETE" and review["outcome"] == "PASS" else "FAIL"
        )
        result["layers"]["zap"] = zap
        result["execution"] = (
            "COMPLETE"
            if all(x["execution"] == "COMPLETE" for x in result["layers"].values())
            else "PARTIAL"
        )
        result["outcome"] = (
            "PASS"
            if all(
                x.get("slice_outcome", x["outcome"]) == "PASS" for x in result["layers"].values()
            )
            else "FAIL"
        )
    finally:
        cleanup(c)
        result["end"] = now()
        write(args.output / "qualification.json", result)
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
