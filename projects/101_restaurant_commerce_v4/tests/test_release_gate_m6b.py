"""The release gate must reject absent, misleading and stale native evidence."""

import copy
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "security"))
from gate import REQUIRED, TEST_MODULES, finding, verdict

NOW = datetime(2026, 11, 3, tzinfo=UTC)
RULES = [
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
]


@pytest.fixture
def proof():
    value = {
        key: {"execution": "COMPLETE", "outcome": "PASS", "finding_count": 0} for key in REQUIRED
    }
    value["baseline"]["checks"] = 11
    value["tests"]["executed_modules"] = sorted(TEST_MODULES)
    value["tests"].update(
        count=400,
        failures=0,
        errors=0,
        skipped=0,
        browser_count=52,
        postgres_fixtures=True,
        postgres_count=100,
        native_exit_code=0,
    )
    value["semgrep"].update(files_scanned=73, missing_source_files=[], native_errors=0)
    value["secrets_config"].update(config_targets=1, source_files=134)
    value["dependencies"].update(
        packages=20, installed_inventory_match=True, database_updated_at="2026-11-02T20:00:00Z"
    )
    value["zap"].update(
        json_body_parse_warnings=0,
        native_log_errors=0,
        server_error_count=0,
        structured_body_coverage_complete=True,
        active_request_count=7000,
        completed_rule_ids=RULES,
        incomplete_rule_ids=[],
        active_protected_success_counts={"staff": 5, "customer": 5},
        budget_exhausted=False,
        protected_counts_are_lower_bounds=False,
    )
    return value


def test_complete_native_proof_can_pass_without_authorizing_money(proof):
    result = verdict(proof, [], [], now=NOW)
    assert result["outcome"] == "PASS" and result["execution"] == "COMPLETE"
    assert result["production_authorization"] is False


@pytest.mark.parametrize("layer", sorted(REQUIRED))
def test_missing_layer_never_passes(proof, layer):
    del proof[layer]
    assert verdict(proof, [], [], now=NOW)["outcome"] == "FAIL"


@pytest.mark.parametrize(
    "layer,key,value",
    [
        ("tests", "count", 0),
        ("tests", "executed_modules", ["test_frontend_m5"]),
        ("tests", "skipped", 1),
        ("tests", "native_exit_code", 124),
        ("tests", "native_exit_code", 1),
        ("tests", "browser_count", 0),
        ("tests", "postgres_count", 0),
        ("tests", "postgres_fixtures", False),
        ("tests", "outcome", "FAIL"),
        ("tests", "outcome", None),
        ("semgrep", "outcome", "BROKEN"),
        ("semgrep", "files_scanned", 0),
        ("semgrep", "native_errors", 1),
        ("semgrep", "missing_source_files", ["security/run.py"]),
        ("dependencies", "packages", 0),
        ("dependencies", "installed_inventory_match", False),
        ("dependencies", "database_updated_at", "2026-10-20T00:00:00Z"),
        ("dependencies", "database_updated_at", "2026-12-20T00:00:00Z"),
        ("dependencies", "database_updated_at", None),
        ("secrets_config", "config_targets", 0),
        ("zap", "json_body_parse_warnings", 1),
        ("zap", "native_log_errors", 1),
        ("zap", "server_error_count", 1),
        ("zap", "structured_body_coverage_complete", False),
        ("zap", "active_request_count", 0),
        ("zap", "completed_rule_ids", ["6"]),
        ("zap", "incomplete_rule_ids", ["6"]),
        ("zap", "budget_exhausted", True),
        ("zap", "protected_counts_are_lower_bounds", True),
        ("zap", "active_protected_success_counts", {"staff": 0, "customer": 5}),
        ("zap", "active_protected_success_counts", {"staff": 5, "customer": 0}),
        ("source_integrity", "outcome", "FAIL"),
    ],
)
def test_incomplete_or_false_success_evidence_fails(proof, layer, key, value):
    proof[layer][key] = value
    # An unrelated informational alert cannot hide native execution failure.
    info = finding("notice", "/", "web application", "INFORMATIONAL", "zap")
    proof["zap"]["finding_count"] = 1
    assert verdict(proof, [info], [], now=NOW)["outcome"] == "FAIL"


def test_review_requires_exact_code_owner_reason_and_expiry(proof):
    issue = finding("rule", "deployment/test.py", "exact source bytes", "ERROR")
    proof["semgrep"].update(outcome="FAIL", finding_count=1)
    review = {
        **issue,
        "owner": "commerce",
        "reason": "Reviewed trusted operator input",
        "expires_at": "2026-12-01T00:00:00+00:00",
    }
    assert verdict(proof, [issue], [review], now=NOW)["outcome"] == "PASS"
    for key, value in [
        ("fingerprint", "changed"),
        ("path", "other.py"),
        ("rule", "other"),
        ("owner", ""),
        ("reason", ""),
        ("expires_at", "2026-11-01T00:00:00+00:00"),
    ]:
        altered = {**review, key: value}
        assert verdict(proof, [issue], [altered], now=NOW)["outcome"] == "FAIL"
    assert verdict(proof, [issue], [review, copy.deepcopy(review)], now=NOW)["outcome"] == "FAIL"
    assert verdict(proof, [issue], [], now=NOW)["outcome"] == "FAIL"


def test_timeout_keeps_command_receipt(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from qualify_operations_m6 import Run

    run = Run(tmp_path / "run")
    with pytest.raises(RuntimeError):
        run.command("timeout", [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.03)
    assert run.commands[0]["exit_code"] == 124
    assert (run.evidence / "timeout.log").exists()


@pytest.mark.parametrize(
    "layer,key",
    [
        ("semgrep", "native_errors"),
        ("semgrep", "missing_source_files"),
        ("zap", "incomplete_rule_ids"),
    ],
)
def test_missing_native_detail_is_not_a_pass(proof, layer, key):
    del proof[layer][key]
    assert verdict(proof, [], [], now=NOW)["outcome"] == "FAIL"
