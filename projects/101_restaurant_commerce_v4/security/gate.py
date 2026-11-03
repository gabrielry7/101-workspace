"""Fail closed on missing execution, stale intelligence, lost auth or new findings."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

REQUIRED = {
    "baseline",
    "tests",
    "semgrep",
    "secrets_config",
    "dependencies",
    "zap",
    "source_integrity",
}


TEST_MODULES = {
    "test_adversarial_m1_m2",
    "test_browser_security",
    "test_customer_safety_m2",
    "test_payment_durability_m3",
    "test_financial_resolution_m3b",
    "test_staff_m4",
    "test_frontend_m5",
    "test_deployment_m6",
    "test_security_gate_m6b",
    "test_release_gate_m6b",
}


def finding(rule, path, evidence, severity, layer="semgrep"):
    return {
        "layer": layer,
        "rule": str(rule),
        "path": str(path),
        "severity": severity,
        "fingerprint": hashlib.sha256(evidence.encode()).hexdigest(),
    }


def verdict(layers, findings, reviews, now=None):
    now = now or datetime.now(UTC)
    failures = []
    for name in sorted(REQUIRED):
        result = layers.get(name, {})
        if result.get("execution") != "COMPLETE":
            failures.append(name + ": incomplete or absent")
        if result.get("outcome") not in {"PASS", "FAIL"}:
            failures.append(name + ": unassessed")
    for name in ["baseline", "tests", "source_integrity"]:
        if layers.get(name, {}).get("outcome") != "PASS":
            failures.append(name + ": mandatory successful execution absent")
    for name in ["semgrep", "secrets_config", "dependencies", "zap"]:
        result = layers.get(name, {})
        actual = sum(item.get("layer") == name for item in findings)
        if result.get("finding_count") != actual:
            failures.append(name + ": finding inventory absent/inconsistent")
        if result.get("outcome") == "FAIL" and not actual:
            failures.append(name + ": native failure without findings")
    baseline = layers.get("baseline", {})
    if baseline.get("checks", 0) < 8 or baseline.get("outcome") != "PASS":
        failures.append("baseline: required real-backend checks missing")
    tests = layers.get("tests", {})
    if (
        tests.get("count", 0) < 1
        or tests.get("failures", -1)
        or tests.get("errors", -1)
        or tests.get("skipped", -1)
    ):
        failures.append("tests: zero, failed or skipped tests")
    if tests.get("native_exit_code") != 0 or tests.get("postgres_count", 0) < 1:
        failures.append("tests: native success/PostgreSQL execution proof missing")
    if tests.get("browser_count", 0) < 1 or tests.get("postgres_fixtures") is not True:
        failures.append("tests: browser/PostgreSQL qualification missing")
    if not TEST_MODULES.issubset(set(tests.get("executed_modules", []))):
        failures.append("tests: mandatory milestone regression modules missing")
    sem = layers.get("semgrep", {})
    if (
        sem.get("files_scanned", 0) < 1
        or sem.get("missing_source_files") != []
        or sem.get("native_errors") != 0
    ):
        failures.append("semgrep: errors or uncovered source files")
    config = layers.get("secrets_config", {})
    if config.get("config_targets", 0) < 1 or config.get("source_files", 0) < 1:
        failures.append("secrets/config: no recognized config or source inventory")
    deps = layers.get("dependencies", {})
    if deps.get("packages", 0) < 19 or deps.get("installed_inventory_match") is not True:
        failures.append("dependencies: deployed inventory not accounted for")
    try:
        age = now - datetime.fromisoformat(deps["database_updated_at"].replace("Z", "+00:00"))
        if age < -timedelta(hours=1) or age > timedelta(hours=48):
            failures.append("dependencies: advisory database stale or future-dated")
    except (KeyError, ValueError, TypeError, AttributeError):
        failures.append("dependencies: advisory database timestamp absent/invalid")
    zap = layers.get("zap", {})
    if (
        zap.get("active_request_count", 0) < 1
        or zap.get("incomplete_rule_ids") != []
        or set(zap.get("completed_rule_ids", []))
        != {
            "6",
            "7",
            "40009",
            "40012",
            "40014",
            "40016",
            "40017",
            "40018",
            "40022",
            "90019",
            "90020",
            "90035",
            "40003",
            "40008",
            "40034",
            "10058",
        }
    ):
        failures.append("zap: no complete active rule coverage")
    counts = zap.get("active_protected_success_counts", {})
    if counts.get("staff", 0) < 1 or counts.get("customer", 0) < 1:
        failures.append("zap: active authenticated staff/customer coverage absent")
    if zap.get("budget_exhausted", True) or zap.get("protected_counts_are_lower_bounds", True):
        failures.append("zap: time budget/export limit prevents complete assessment")
    accepted, blocked = [], []
    for item in findings:
        if item["severity"] == "INFORMATIONAL":
            continue
        matches = [
            r
            for r in reviews
            if all(
                r.get(k) == item[k] for k in ("rule", "path", "fingerprint", "layer", "severity")
            )
        ]
        valid = []
        for r in matches:
            try:
                if (
                    r.get("reason")
                    and r.get("owner")
                    and datetime.fromisoformat(r["expires_at"]) > now
                ):
                    valid.append(r)
            except (KeyError, ValueError, TypeError, AttributeError):
                pass
        (accepted if len(valid) == 1 else blocked).append(item)
    if blocked:
        failures.append(f"findings: {len(blocked)} without exact current review")
    # A native FAIL must have an actual finding; missing/invented detail cannot clear it.
    if any(r.get("outcome") == "FAIL" for r in layers.values()) and not findings:
        failures.append("native FAIL without findings cannot be waived")
    return {
        "execution": "COMPLETE"
        if all(layers.get(n, {}).get("execution") == "COMPLETE" for n in REQUIRED)
        else "PARTIAL",
        "outcome": "FAIL" if failures else "PASS",
        "failures": failures,
        "accepted_findings": accepted,
        "blocking_findings": blocked,
        "production_authorization": False,
    }


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str) + "\n")
