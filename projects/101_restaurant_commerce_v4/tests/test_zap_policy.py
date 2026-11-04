import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "zap_policy", Path(__file__).parents[1] / "adversarial/zap_policy.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def inventory():
    return [{"id": k, "name": k} for k in set(m.BASE) | set(m.ADDED) | set(m.EXCLUDED)]


def test_policy_maps_every_installed_rule_and_expands_only_local_rules():
    p = m.policy(inventory(), expanded=True)
    assert len(p["selected"]) == 19
    assert set(p["added"]) == {"0", "40035", "10104"}
    assert all(r["reason"] for r in p["rules"])
    assert not set(p["selected"]) & {"20019", "40043", "90023", "90034"}


@pytest.mark.parametrize("change", ["new", "missing", "dependency"])
def test_policy_fails_closed_on_inventory_drift(change):
    rows = inventory()
    if change == "new":
        rows.append({"id": "new", "name": "unreviewed"})
    if change == "missing":
        rows = [r for r in rows if r["id"] != "6"]
    if change == "dependency":
        next(r for r in rows if r["id"] == "6")["allDependenciesAvailable"] = "false"
    with pytest.raises(ValueError):
        m.policy(rows, expanded=True)


def test_zero_messages_are_not_execution_proof():
    result = m.execution_coverage(
        {
            "x": [
                {"Plugin": ["Get", "10058", "release", "Complete", "10", "0", "0"]},
                {"Plugin": ["XSS", "40012", "release", "Complete", "10", "4", "0"]},
            ]
        },
        ["10058", "40012", "missing"],
    )
    assert [r["execution"] for r in result] == ["NOT RUN", "COMPLETE", "NOT RUN"]
