#!/usr/bin/env python3
"""Execute independent local suites sequentially; never turn missing layers green."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--native-tools", required=True, type=Path)
    args = p.parse_args()
    args.output = args.output.absolute()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    records = []
    env = dict(os.environ)
    # Existing run.sh installs the current requirements, not a stale environment.
    commands = [
        (
            "adversarial",
            [
                str(ROOT / "adversarial/run.sh"),
                "--run-dir",
                str(args.output / "journeys"),
                "--layers",
                "baseline,financial,authorization,races,browser,properties,schemathesis,locust,faults",
            ],
        ),
        (
            "security",
            [
                sys.executable,
                str(ROOT / "security/check.py"),
                "--run-dir",
                str(args.output / "security"),
                "--cache",
                str(args.cache.absolute()),
                "--native-tools",
                str(args.native_tools.absolute()),
                "--test-python",
                sys.executable,
            ],
        ),
    ]
    for name, command in commands:
        start = datetime.now(UTC).isoformat()
        with (args.output / (name + ".log")).open("w") as log:
            result = subprocess.run(
                command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        records.append(
            dict(
                layer=name,
                command=command,
                start=start,
                end=datetime.now(UTC).isoformat(),
                exit_code=result.returncode,
                outcome="PASS" if result.returncode == 0 else "FAIL",
                evidence=str(args.output / ("journeys" if name == "adversarial" else "security")),
            )
        )
        (args.output / "commands.json").write_text(json.dumps(records, indent=2))
    strix = dict(
        execution="BLOCKED",
        outcome="NOT RUN",
        model_calls=0,
        reason=(
            "USD0: no explicitly configured no-cost model backend. Do not "
            "infer authorization from saved keys."
        ),
        executables={name: shutil.which(name) for name in ("strix", "docker", "ollama")},
    )
    assessment = dict(
        execution="PARTIAL",
        outcome="FAIL" if any(r["exit_code"] for r in records) else "UNASSESSED",
        layers=records,
        strix=strix,
        production_authorization=False,
        runtime_limits=[
            (
                "Journeys use installed application, two API workers, separate "
                "recovery and durable provider."
            ),
            "Security deployment separately verifies locked release with separate recovery worker.",
            (
                "Faults use the installed recovery runner; deployment lifecycle "
                "is qualified separately."
            ),
        ],
    )
    (args.output / "assessment.json").write_text(json.dumps(assessment, indent=2))
    print(json.dumps(assessment, indent=2))
    # Explicitly non-green while the requested Strix assessment is not executed.
    return 1 if any(r["exit_code"] for r in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
