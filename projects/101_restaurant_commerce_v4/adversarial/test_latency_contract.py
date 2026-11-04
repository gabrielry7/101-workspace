from copy import deepcopy

from latency_contract import TARGETS, assess


def receipt():
    return {
        "profile": "normal",
        "outcome": "PASS",
        "counts": {
            "operations": [
                {
                    "name": name,
                    "requests": 10,
                    "failures": 0,
                    "p50_ms": limits[0],
                    "p95_ms": limits[1],
                    "p99_ms": limits[2],
                }
                for name, limits in TARGETS["normal"].items()
            ]
        },
    }


def test_threshold_boundary_and_slow_success_are_distinct():
    r = receipt()
    assert assess(r)["outcome"] == "PASS"
    r["counts"]["operations"][0]["p95_ms"] += 1
    assert assess(r)["outcome"] == "FAIL"


def test_missing_empty_failed_or_incorrect_runs_never_pass():
    for mutation in ["missing", "empty", "error", "integrity"]:
        r = deepcopy(receipt())
        if mutation == "missing":
            r["counts"]["operations"].pop()
        if mutation == "empty":
            r["counts"]["operations"][0]["requests"] = 0
        if mutation == "error":
            r["counts"]["operations"][0]["failures"] = 1
        if mutation == "integrity":
            r["outcome"] = "FAIL"
        assert assess(r)["outcome"] == "FAIL"


def test_warmup_is_not_latency_qualification():
    r = receipt()
    r["profile"] = "warmup"
    assert assess(r)["outcome"] == "NOT RUN"
