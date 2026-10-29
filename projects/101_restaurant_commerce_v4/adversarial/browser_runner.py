"""Execute the live Playwright layer and preserve native reports and traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--skip-agents", action="store_true")
    a = p.parse_args()
    cfg = json.loads(a.config.read_text())
    if urlsplit(cfg["base_url"]).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Only loopback targets allowed")
    output = a.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(
            "Use a fresh browser output directory; prior evidence will not be overwritten"
        )
    output.mkdir(parents=True, exist_ok=True)
    cwd = Path(__file__).resolve().parent / "browser"
    if not (cwd / "node_modules/playwright/cli.js").exists():
        with (output / "npm-install.log").open("w") as log:
            result = subprocess.run(
                ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=180,
                check=False,
            )
        if result.returncode:
            (output / "summary.json").write_text(
                json.dumps(
                    {
                        "layer": "playwright",
                        "execution": "BLOCKED",
                        "outcome": "UNASSESSED",
                        "executed": 0,
                        "blocker": "npm ci failed; see npm-install.log",
                        "exit_code": result.returncode,
                    },
                    indent=2,
                )
            )
            return result.returncode
    env = {
        **os.environ,
        "COMMERCE_RUN_CONFIG": str(a.config.resolve()),
        "COMMERCE_BROWSER_OUTPUT": str(output),
    }
    started = datetime.now(UTC).isoformat()
    tick = time.monotonic()
    agent_runs = []

    def agent_phase(phase, calls_file):
        target = output / "agents" / phase
        target.mkdir(parents=True, exist_ok=True)
        agent_env = {**env, "COMMERCE_BROWSER_OUTPUT": str(target)}
        agent_cmd = [
            __import__("sys").executable,
            "agent_probe.py",
            "--output",
            str(target),
            "--calls",
            str(calls_file),
        ]
        with (target / "execution.log").open("w") as log:
            try:
                agent_code = subprocess.run(
                    agent_cmd,
                    cwd=cwd,
                    env=agent_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=240,
                    check=False,
                ).returncode
            except subprocess.TimeoutExpired:
                agent_code = 124
        native_agent = target / "mcp-native.json"
        native_result = (
            json.loads(native_agent.read_text()) if native_agent.exists() else {}
        )
        agent_runs.append(
            {
                "phase": phase,
                "command": agent_cmd,
                "exit_code": agent_code,
                "native": str(native_agent),
                "execution": native_result.get("execution", "BLOCKED"),
                "tool_calls": native_result.get("executed_tool_calls", 0),
                "tool_errors": native_result.get("tool_errors"),
            }
        )

    if not a.skip_agents:
        for phase in ["planner", "generator"]:
            agent_phase(phase, cwd / "specs" / (phase + "-calls.json"))
    cmd = ["node", "node_modules/playwright/cli.js", "test"]
    version = subprocess.run(
        ["node", "node_modules/playwright/cli.js", "--version"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    with (output / "execution.log").open("w") as f:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=420)
        except subprocess.TimeoutExpired:
            code = 124
        finally:
            # Only this invocation's own process group; includes test/browser children.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    native = output / "playwright.json"
    counts = {}
    if native.exists():
        data = json.loads(native.read_text())
        stats = data.get("stats", {})
        counts = {
            k: stats.get(k, 0) for k in ["expected", "unexpected", "flaky", "skipped"]
        }
    executed = (
        counts.get("expected", 0) + counts.get("unexpected", 0) + counts.get("flaky", 0)
    )
    if not a.skip_agents and native.exists() and executed:

        def failed_specs(suites):
            for suite in suites:
                for spec in suite.get("specs", []):
                    if any(
                        t.get("status") == "unexpected" for t in spec.get("tests", [])
                    ):
                        yield spec
                yield from failed_specs(suite.get("suites", []))

        failed = next(failed_specs(data.get("suites", [])), None)
        if failed:
            calls = [
                {
                    "name": "test_run",
                    "arguments": {
                        "locations": [failed["file"] + ":" + str(failed["line"])]
                    },
                },
                {
                    "name": "test_debug",
                    "arguments": {
                        "test": {"id": failed["id"], "title": failed["title"]}
                    },
                },
                {"name": "browser_snapshot", "arguments": {}},
            ]
        else:
            calls = [
                {
                    "name": "test_run",
                    "arguments": {"locations": ["tests/agent-catalog.spec.ts"]},
                }
            ]
        calls_file = output / "healer-calls.json"
        calls_file.write_text(json.dumps(calls, indent=2))
        agent_phase("healer", calls_file)
    browser_version = subprocess.run(
        ["/usr/bin/chromium", "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    result = {
        "layer": "playwright",
        "chromium_version": browser_version,
        "command": cmd,
        "version": version,
        "target": cfg["base_url"],
        "revision": cfg.get("revision"),
        "wheel_sha256": cfg.get("wheel_sha256"),
        "test_files_sha256": {
            str(f.relative_to(cwd)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in (cwd / "tests").glob("*.ts")
        },
        "started_at": started,
        "ended_at": datetime.now(UTC).isoformat(),
        "duration_seconds": time.monotonic() - tick,
        "exit_code": code,
        "execution": "COMPLETE"
        if executed
        and code != 124
        and all(x["execution"] == "COMPLETE" for x in agent_runs)
        else "PARTIAL",
        "outcome": "PASS"
        if code == 0 and executed > 0 and not counts.get("skipped")
        else "FAIL"
        if executed
        else "UNASSESSED",
        "executed": executed,
        "counts": counts,
        "native_report": str(native),
        "agent_runs": agent_runs,
        "coverage_gaps": [
            "No customer login exists; capability reads are exercised instead",
            "No distinct staff identities or per-business token scope exists; failure retained",
            "Physical low-end/older-browser coverage not claimed",
        ],
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["outcome"] == "PASS" and result["execution"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
