"""P07 local qualification targets, declared before the P05 experiment (milliseconds).

These are engineering targets, not achieved production SLAs. Warmup is excluded.
Zero native failures and actual financial/capacity correctness are separate gates.
"""

TARGETS = {
    "normal": {
        "checkout": (500, 1000, 1500),
        "storefront": (100, 300, 500),
        "quote": (200, 500, 1000),
        "checkout-exact-replay": (200, 600, 1000),
        "payment-complete": (300, 800, 1500),
        "order-status": (200, 600, 1000),
    },
    "spike": {
        "checkout": (2000, 4000, 6000),
        "storefront": (300, 800, 1200),
        "quote": (600, 1500, 2500),
        "checkout-exact-replay": (600, 1500, 2500),
        "payment-complete": (1000, 2500, 4000),
        "order-status": (600, 1500, 2500),
    },
}


def assess(receipt):
    targets = TARGETS.get(receipt["profile"])
    if not targets:
        return {"outcome": "NOT RUN", "reason": "Warmup, not a steady-load gate"}
    actual = {op["name"]: op for op in receipt["counts"]["operations"]}
    checks = []
    for name, limits in targets.items():
        row = actual.get(name)
        if not row or row["requests"] <= 0:
            checks.append({"operation": name, "outcome": "NOT RUN"})
            continue
        values = [row[k] for k in ("p50_ms", "p95_ms", "p99_ms")]
        checks.append(
            {
                "operation": name,
                "actual_ms": values,
                "limits_ms": list(limits),
                "outcome": "PASS"
                if row["failures"] == 0 and all(v <= t for v, t in zip(values, limits, strict=True))
                else "FAIL",
            }
        )
    return {
        "outcome": "PASS"
        if receipt["outcome"] == "PASS" and all(c["outcome"] == "PASS" for c in checks)
        else "FAIL",
        "checks": checks,
    }
