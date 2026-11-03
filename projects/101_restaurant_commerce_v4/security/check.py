#!/usr/bin/env python3
"""Prepare free local tools, then qualify a fresh disposable deployment.

Linux x86_64, Python3.12, uv, PostgreSQL tools/libpq, Chromium and Node/npm required.
Downloads public tools/advisories only. No hosted jobs, model calls or live providers.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adversarial"))
import scanners  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--test-python", help="Reuse an explicitly selected existing test-tool environment"
    )
    parser.add_argument("--native-tools", help="Reuse task-owned Trivy/ZAP/Java installs")
    args = parser.parse_args()
    cache = Path(args.cache).resolve()
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if Path(args.run_dir).exists():
        raise ValueError("Run directory must be new; existing evidence is never overwritten")
    rec = scanners.Recorder(cache / "bootstrap", {})

    def command(name, argv, timeout=600):
        result = rec.run(name, [str(x) for x in argv], timeout, cwd=ROOT)
        if result["exit_code"] != 0:
            raise RuntimeError(name + " failed; see bootstrap command receipt/log")

    python = Path(args.test_python).absolute() if args.test_python else cache / "tests/bin/python"
    if not args.test_python:
        if not python.exists():
            command("test-venv", ["uv", "venv", "--python", "3.12", "--seed", cache / "tests"])
        command(
            "test-dependencies",
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "-r",
                ROOT / "adversarial/requirements-tools.txt",
            ],
        )
    command(
        "runtime-wheels",
        [
            python,
            "-m",
            "pip",
            "download",
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            ROOT / "deployment/requirements.lock",
            "-d",
            cache / "wheels",
        ],
    )
    scanners.TOOLCHAIN = (
        Path(args.native_tools).resolve() if args.native_tools else cache / "native"
    )
    scanners.bootstrap(rec, ["trivy", "zap"])
    if any(row["exit_code"] != 0 for row in rec.rows):
        raise RuntimeError("Native tool bootstrap incomplete")
    semgrep = cache / "semgrep/bin/semgrep"
    if not semgrep.exists():
        command("semgrep-venv", ["uv", "venv", "--python", "3.12", cache / "semgrep"])
        command(
            "semgrep-install",
            ["uv", "pip", "install", "--python", cache / "semgrep/bin/python", "semgrep==1.182.1"],
        )
    command("semgrep-version", [semgrep, "--version"])
    rules = cache / "rules"
    rules.mkdir(exist_ok=True)
    lock = json.loads((ROOT / "security/rules.lock.json").read_text())
    for pack in lock["packs"]:
        target = rules / (pack["name"] + ".yaml")
        if not target.exists():
            with urlopen("https://semgrep.dev/c/p/" + pack["name"], timeout=60) as response:
                body = response.read()
            if hashlib.sha256(body).hexdigest() != pack["sha256"]:
                raise ValueError(
                    "Rule registry changed; review and update rules.lock.json explicitly"
                )
            target.write_bytes(body)
        if hashlib.sha256(target.read_bytes()).hexdigest() != pack["sha256"]:
            raise ValueError("Local rule hash mismatch")
    axe = os.environ.get("COMMERCE_AXE_PATH")
    if not axe:
        command(
            "axe-install",
            [
                "npm",
                "install",
                "--prefix",
                cache / "browser",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
                "axe-core@4.10.2",
            ],
        )
        axe = str(cache / "browser/node_modules/axe-core/axe.min.js")
    env = {**os.environ, "COMMERCE_AXE_PATH": axe}
    argv = [
        python,
        "-B",
        ROOT / "security/run.py",
        "--run-dir",
        Path(args.run_dir).resolve(),
        "--wheelhouse",
        cache / "wheels",
        "--tool-root",
        scanners.TOOLCHAIN,
        "--semgrep",
        semgrep,
        "--rules-dir",
        rules,
        "--trivy-cache",
        cache / "trivy-cache",
    ]
    return subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
