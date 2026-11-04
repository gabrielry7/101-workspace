"""Bound native Schemathesis execution and reject empty/404-only qualification."""

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
from load_contract import validate_target
from run import command
from scanner_contract import record_operations


def run_records(config, config_path, output):
    validate_target(config, config_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    spec = httpx.get(config["base_url"] + "/openapi.json", trust_env=False).json()
    required = [method + " " + path for method, path in record_operations(spec)]
    env = dict(
        os.environ,
        PYTHONPATH=config["installed"] + os.pathsep + str(Path(__file__).parent),
        COMMERCE_RECORD_CONFIG=str(Path(config_path).resolve()),
        COMMERCE_RECORD_OUTPUT=str(output / "requests.jsonl"),
    )
    started = datetime.now(UTC).isoformat()
    execution_config = {**config, "run_dir": str(output)}
    code = command(
        execution_config,
        "record-fuzz",
        [
            config["python"],
            "-m",
            "pytest",
            "-q",
            "-x",
            Path(__file__).with_name("record_fuzz.py"),
            "--junitxml=" + str(output / "junit.xml"),
        ],
        timeout=300,
        env=env,
    )
    rows = (
        [json.loads(line) for line in (output / "requests.jsonl").read_text().splitlines()]
        if (output / "requests.jsonl").exists()
        else []
    )
    operations = {}
    for op in required:
        cases = [r for r in rows if r["method"] + " " + r["path"] == op]
        operations[op] = {
            "valid_statuses": [r["status"] for r in cases if r["label"] == "valid"],
            "generated": sum(r["label"] == "generated" for r in cases),
            "statuses": dict(Counter(str(r["status"]) for r in cases)),
        }
    covered = bool(required) and all(
        v["generated"] > 0 and v["valid_statuses"] == [409 if op.endswith("/sent") else 200]
        for op, v in operations.items()
    )
    result = {
        "execution": "COMPLETE" if code == 0 and covered else "PARTIAL",
        "outcome": "PASS" if code == 0 and covered else "FAIL",
        "revision": config["revision"],
        "wheel_sha256": config["wheel_sha256"],
        "start": started,
        "end": datetime.now(UTC).isoformat(),
        "exit_code": code,
        "requests": len(rows),
        "protected_tables": sorted(
            {name for row in rows for name in row.get("protected_tables", [])}
        ),
        "operations": operations,
        "excluded_optional_routes": [p for p in spec["paths"] if "/loyalty-refunds/" in p],
        "gaps": [
            "Body/query generation plus explicit valid-record examples; not exhaustive sequences.",
            "Manual sent endpoint intentionally rejects409; no delivery receipt fabricated.",
            "Optional loyalty configuration is disabled; preview and loyalty-refund allocation "
            "routes are not covered.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
