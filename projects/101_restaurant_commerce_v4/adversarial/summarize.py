"""Collect native receipts without turning tool exit codes into unsupported passes."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


def native(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return {"execution": "PARTIAL", "outcome": "UNASSESSED", "blocker": str(exc)}


def summarize(config):
    root = Path(config["run_dir"])
    layers = {}
    for name, filename in {
        "browser": "browser/summary.json",
        "properties": "properties/receipt.json",
        "schemathesis": "schemathesis/summary.json",
        "locust": "locust/summary.json",
        "faults": "faults/receipt.json",
        "scanners": "scanners/summary.json",
    }.items():
        path = root / filename
        layers[name] = (
            native(path)
            if path.exists()
            else {
                "execution": "BLOCKED",
                "outcome": "UNASSESSED",
                "blocker": "No native receipt in this run; see command log or selected layer list",
            }
        )
    baseline_attempts = []
    for stem in ["existing-tests", "baseline-retry"]:
        receipt_path = root / (stem + ".receipt.json")
        if not receipt_path.exists():
            continue
        row = native(receipt_path)
        path = root / (stem + ".xml")
        result = {
            "receipt": str(receipt_path),
            "execution": "PARTIAL",
            "outcome": "UNASSESSED",
        }
        try:
            suites = list(ET.parse(path).getroot().iter("testsuite"))
            totals = {
                key: sum(int(s.get(key, 0)) for s in suites)
                for key in ["tests", "failures", "errors", "skipped"]
            }
            started = datetime.fromisoformat(row["start"]).timestamp()
            fresh = path.stat().st_mtime >= started
            same_artifact = row.get("wheel_sha256") == config.get("wheel_sha256")
            valid = (
                row.get("exit_code") in (0, 1)
                and fresh
                and same_artifact
                and totals["tests"] > 0
            )
            result.update(totals)
            result.update(
                execution="COMPLETE" if valid else "PARTIAL",
                outcome="PASS"
                if valid
                and row.get("exit_code") == 0
                and not any(totals[x] for x in ["failures", "errors", "skipped"])
                else "FAIL",
                fresh_xml=fresh,
                same_artifact=same_artifact,
                exit_code=row.get("exit_code"),
            )
        except (OSError, ValueError, KeyError, ET.ParseError) as exc:
            result["blocker"] = str(exc)
        baseline_attempts.append(result)
    layers["baseline"] = {
        "attempts": baseline_attempts,
        "execution": "COMPLETE"
        if baseline_attempts and baseline_attempts[-1]["execution"] == "COMPLETE"
        else "PARTIAL",
        "outcome": baseline_attempts[-1]["outcome"]
        if baseline_attempts
        else "UNASSESSED",
    }
    layers["skills"] = {
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
        "evidence": "adversarial/skill_review.md",
        "gap": "Five procedures manually applied; native Trail of Bits workflow not fully executed",
    }
    result = {
        "revision": config["revision"],
        "wheel_sha256": config.get("wheel_sha256"),
        "target": config["base_url"],
        "layers": layers,
        "limits": [
            "Synthetic providers; no live money or messages",
            "Customer login, scoped staff identities, standalone worker absent",
            "Local budgets do not qualify production capacity or physical old devices",
            "Original attachment unavailable; budgets documented in README",
        ],
    }
    (root / "assessment.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
