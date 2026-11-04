"""S03: optional loyalty HTTP invariants plus explicitly mapped native ZAP policy."""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from run import (
    PYTHON,
    ROOT,
    baseline_journey,
    cleanup,
    command,
    now,
    process,
    setup,
    stop,
    wait_http,
    write,
)


def enable_optional(c):
    from sqlalchemy import create_engine
    from world_model.restaurant_commerce.loyalty_execution_migrations import (
        upgrade_loyalty_execution,
    )
    from world_model.restaurant_commerce.loyalty_migrations import upgrade_loyalty_configuration

    stop(c, "application")
    engine = create_engine(c["database_url"])
    upgrade_loyalty_configuration(engine)
    upgrade_loyalty_execution(engine)
    engine.dispose()
    c["loyalty_configuration_enabled"] = True
    c["zap_expanded_policy"] = True
    write(Path(c["run_dir"]) / "config.json", c)
    env = dict(
        os.environ,
        COMMERCE_TEST_CONFIG=str(Path(c["run_dir"]) / "config.json"),
        PYTHONPATH=c["installed"],
    )
    process(
        c,
        "application",
        [
            PYTHON,
            "-m",
            "uvicorn",
            "runtime:application",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            c["app_port"],
            "--workers",
            "2",
        ],
        env,
    )
    wait_http(c["base_url"] + "/ready")
    stop(c, "recovery")
    write(Path(c["run_dir"]) / "config.json", c)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scanner-tools", type=Path, required=True)
    parser.add_argument(
        "--no-scan", action="store_true", help="Diagnostic tests only; never a full S03 pass"
    )
    args = parser.parse_args()
    result = {"start": now(), "execution": "PARTIAL", "outcome": "UNASSESSED", "layers": {}}
    c = setup(args.output.resolve())
    result.update(revision=c["revision"], wheel_sha256=c["wheel_sha256"])
    try:
        baseline_journey(c)
        enable_optional(c)
        env = dict(
            os.environ,
            PYTHONPATH=c["installed"] + os.pathsep + str(ROOT / "adversarial"),
            COMMERCE_RECORD_CONFIG=str(args.output.resolve() / "config.json"),
            COMMERCE_PAYMENT_TEST_DATABASE_URL=c["database_url"],
        )
        for name, files, budget in [
            ("loyalty-live", ["adversarial/test_loyalty_security_live.py"], 240),
            ("browser-security", ["adversarial/security_browser.py"], 90),
            (
                "regressions",
                [
                    "tests/test_zap_policy.py",
                    "tests/test_loyalty_security_validation.py",
                    "tests/test_loyalty_execution.py",
                    "tests/test_loyalty_assignment.py",
                    "tests/test_loyalty_rules.py",
                    "tests/test_loyalty_configuration.py",
                    "tests/test_scanner_contract.py",
                    "tests/test_zap_alert_review.py",
                ],
                300,
            ),
        ]:
            code = command(
                c,
                name,
                [
                    PYTHON,
                    "-m",
                    "pytest",
                    "-q",
                    *files,
                    "--junitxml=" + str(args.output.resolve() / (name + ".xml")),
                ],
                env=env,
                timeout=budget,
            )
            junit = args.output / (name + ".xml")
            suites = list(ET.parse(junit).getroot().iter("testsuite")) if junit.exists() else []
            counts = {
                k: sum(int(x.get(k, 0)) for x in suites)
                for k in ["tests", "failures", "errors", "skipped"]
            }
            qualified = (
                code == 0
                and counts["tests"] > 0
                and not any(counts[k] for k in ["failures", "errors", "skipped"])
            )
            result["layers"][name] = {
                "exit_code": code,
                "counts": counts,
                "execution": "COMPLETE" if suites and code not in {124, 127} else "PARTIAL",
                "outcome": "PASS" if qualified else "FAIL",
            }
        if args.no_scan:
            result["layers"]["zap"] = {
                "execution": "NOT RUN",
                "outcome": "UNASSESSED",
                "reason": "--no-scan diagnostic",
            }
        else:
            import scanners
            from loyalty_security import ALLOCATION, PREVIEW, LoyaltyFixtures

            f = LoyaltyFixtures(c)
            try:
                ids, body = f.preview()
                aids, abody, allocation_info = f.allocation()
                c["zap_operation_fixtures"] = {
                    "POST " + PREVIEW: {"ids": ids, "body": body},
                    "POST " + ALLOCATION: {"ids": aids, "body": abody},
                }
                write(args.output / "config.json", c)
                # Prove both fixtures and an allocation replay work before ZAP imports them.
                f.call("POST", PREVIEW.format(**ids), body)
                f.call("POST", ALLOCATION.format(**aids), abody)
                f.call("POST", ALLOCATION.format(**aids), abody)
                scanners.TOOLCHAIN = args.scanner_tools
                rec = scanners.Recorder(args.output / "private-zap", c)
                zap = scanners.zap_scan(rec, c)
                write(rec.output / "result.json", zap)
                sys.path.insert(0, str(ROOT / "security"))
                from alert_review import reviewed_alerts

                alert_path = rec.output / "zap-alerts.json"
                alerts = (
                    json.loads(alert_path.read_text()).get("alerts", [])
                    if alert_path.exists()
                    else []
                )
                review = reviewed_alerts(alerts, c["base_url"], ROOT)
                write(args.output / "zap-review.json", review)
                added = [
                    r
                    for r in zap.get("rule_execution_coverage", [])
                    if r["id"] in {"0", "40035", "10104"}
                ]
                expanded = len(added) == 3 and all(r["execution"] == "COMPLETE" for r in added)
                structured = zap.get("structured_body_coverage", {})
                optional = [
                    v for k, v in structured.items() if k.endswith(("/preview", "/allocation"))
                ]
                optional_covered = len(optional) == 2 and all(
                    v["active_json"] > 0 and v["nested_mutations"] > 0 for v in optional
                )
                zap["slice_outcome"] = (
                    "PASS"
                    if (
                        zap["execution"] == "COMPLETE"
                        and review["outcome"] == "PASS"
                        and zap.get("structured_body_coverage_complete")
                        and expanded
                        and optional_covered
                        and not zap.get("server_error_count")
                        and not zap.get("json_body_parse_warnings")
                        and not zap.get("native_log_errors")
                    )
                    else "FAIL"
                )
                from sqlalchemy import func, select
                from sqlalchemy.orm import Session
                from world_model.restaurant_commerce.loyalty_execution_models import (
                    LoyaltyRefundAllocation,
                )
                from world_model.restaurant_commerce.loyalty_wallet import reconcile
                from world_model.restaurant_commerce.models import LoyaltyAccount

                with Session(f.engine) as session:
                    account = session.get(LoyaltyAccount, allocation_info["account_id"])
                    allocations = session.scalar(
                        select(func.count())
                        .select_from(LoyaltyRefundAllocation)
                        .where(LoyaltyRefundAllocation.refund_id == aids["refund_id"])
                    )
                    allocation = session.get(LoyaltyRefundAllocation, aids["refund_id"])
                    invariant = {
                        "allocations": allocations,
                        "document_unchanged": allocation is not None
                        and json.loads(allocation.document) == abody,
                        "points": account.available_points,
                        "expected_points": 2 * ((allocation_info["total_minor"] - 1001) // 1000),
                        "wallet_reconciled": reconcile(session, account)["reconciled"],
                    }
                invariant["outcome"] = (
                    "PASS"
                    if (
                        allocations == 1
                        and invariant["document_unchanged"]
                        and invariant["points"] == invariant["expected_points"]
                        and invariant["wallet_reconciled"]
                    )
                    else "FAIL"
                )
                write(args.output / "scanner-wallet-invariant.json", invariant)
                if invariant["outcome"] != "PASS":
                    zap["slice_outcome"] = "FAIL"
                zap["wallet_invariant"] = invariant
                zap["added_rule_coverage_complete"] = expanded
                zap["optional_route_coverage_complete"] = optional_covered
                result["layers"]["zap"] = zap
            finally:
                f.close()
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
    except Exception as exc:
        result["error"] = str(exc)
        result["outcome"] = "FAIL"
        raise
    finally:
        cleanup(c)
        result["end"] = now()
        write(args.output / "qualification.json", result)
    return 0 if result["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
