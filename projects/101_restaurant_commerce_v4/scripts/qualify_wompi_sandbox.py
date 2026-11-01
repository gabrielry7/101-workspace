#!/usr/bin/env python3
"""Build an isolated artifact, run Wompi qualification layers, retain evidence.

No cloud provisioning. Remote fake-money probes require --execute-sandbox.
Only this run's PostgreSQL cluster is stopped; all evidence is retained.
"""

import argparse
import getpass
import hashlib
import importlib.metadata
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adversarial"))
from run import command  # noqa: E402 - reuse command timeouts and native receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--layers", default="tests,postgres,receiver")
    parser.add_argument("--execute-sandbox", action="store_true")
    parser.add_argument("--cloudflared", type=Path)
    parser.add_argument(
        "--financial",
        action="store_true",
        help="Also execute financial contract tests in the PostgreSQL layer",
    )
    args = parser.parse_args()
    layers = args.layers.split(",")
    if not layers or set(layers) - {"tests", "postgres", "receiver", "remote", "hosted"}:
        parser.error("Choose nonempty tests,postgres,receiver,remote,hosted layers")
    if set(layers) & {"remote", "hosted"} and not args.execute_sandbox:
        parser.error("remote requires --execute-sandbox")
    if "hosted" in layers and not args.cloudflared:
        parser.error("hosted requires --cloudflared path to the official executable")
    root = args.run_dir.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    c = {
        "run_dir": str(root),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty_paths": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "base_url": "disposable-loopback-only",
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "versions": {
            n: importlib.metadata.version(n)
            for n in ("pytest", "hypothesis", "sqlalchemy", "httpx")
        },
        "layers": {},
        "gaps": [
            "Offline layers do not exercise native webhook delivery; "
            "see separate native qualification.",
            "Real-money operation remains disabled.",
        ],
    }
    env = dict(os.environ)
    env["COMMERCE_BROWSER_EXECUTABLE"] = env.get("COMMERCE_BROWSER_EXECUTABLE", "/usr/bin/chromium")
    env.pop("COMMERCE_PAYMENT_TEST_DATABASE_URL", None)
    started = False
    try:
        for name, cmd in [
            (
                "build",
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "-w",
                    str(root / "wheel"),
                    str(ROOT),
                ],
            ),
        ]:
            if command(c, name, cmd, env=env) != 0:
                raise RuntimeError(name + " failed; see native report")
        wheels = list((root / "wheel").glob("*.whl"))
        assert len(wheels) == 1
        c["wheel_sha256"] = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
        if (
            command(
                c,
                "install",
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(root / "installed"),
                    str(wheels[0]),
                ],
                env=env,
            )
            != 0
        ):
            raise RuntimeError("install failed")
        env["PYTHONPATH"] = str(root / "installed")
        for layer in layers:
            if layer == "postgres":
                missing = [x for x in ("initdb", "pg_ctl", "createdb") if not shutil.which(x)]
                if missing:
                    c["layers"][layer] = {
                        "execution": "BLOCKED",
                        "outcome": "UNASSESSED",
                        "reason": "Missing " + ",".join(missing),
                    }
                    continue
                with socket.socket() as s:
                    s.bind(("127.0.0.1", 0))
                    port = s.getsockname()[1]
                if (
                    command(
                        c,
                        "initdb",
                        [
                            "initdb",
                            "-D",
                            str(root / "pgdata"),
                            "-A",
                            "trust",
                            "--no-locale",
                            "--encoding=UTF8",
                        ],
                        env=env,
                    )
                    != 0
                ):
                    raise RuntimeError("initdb failed")
                if (
                    command(
                        c,
                        "postgres-start",
                        [
                            "pg_ctl",
                            "-D",
                            str(root / "pgdata"),
                            "-l",
                            str(root / "postgres-server.log"),
                            "-o",
                            f"-h 127.0.0.1 -p {port} -k {root}",
                            "-w",
                            "start",
                        ],
                        env=env,
                    )
                    != 0
                ):
                    raise RuntimeError("postgres start failed")
                started = True
                if (
                    command(
                        c,
                        "createdb",
                        ["createdb", "-h", "127.0.0.1", "-p", str(port), "wompi_edges"],
                        env=env,
                    )
                    != 0
                ):
                    raise RuntimeError("createdb failed")
                env["COMMERCE_PAYMENT_TEST_DATABASE_URL"] = (
                    f"postgresql+psycopg://{getpass.getuser()}@127.0.0.1:{port}/wompi_edges"
                )
            if layer in ("tests", "postgres"):
                test_paths = (
                    ["tests"]
                    if layer == "tests"
                    else ["tests/test_wompi_sandbox.py", "tests/test_wompi_adversarial.py"]
                )
                if layer == "postgres" and args.financial:
                    test_paths.extend(
                        ["tests/test_financial_resolution_m3b.py", "tests/test_wompi_financial.py"]
                    )
                xml = root / (layer + ".xml")
                code = command(
                    c,
                    layer,
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        *test_paths,
                        "--tb=short",
                        "--hypothesis-show-statistics",
                        "--junitxml=" + str(xml),
                    ],
                    timeout=600,
                    env=env,
                )
                counts = {}
                if xml.exists():
                    suites = ET.parse(xml).getroot().findall("testsuite")
                    counts = {
                        k: sum(int(x.get(k, 0)) for x in suites)
                        for k in ("tests", "failures", "errors", "skipped")
                    }
                ok = code == 0 and counts.get("tests", 0) > 0 and counts.get("skipped", 0) == 0
                c["layers"][layer] = {
                    "execution": "COMPLETE" if counts.get("tests", 0) > 0 else "PARTIAL",
                    "outcome": "PASS" if ok else "FAIL",
                    "counts": counts,
                    "exit_code": code,
                }
                env.pop("COMMERCE_PAYMENT_TEST_DATABASE_URL", None)
            elif layer == "receiver":
                code = command(c, layer, ["node", "sandbox_receiver/test.mjs"], env=env)
                c["layers"][layer] = {
                    "execution": "COMPLETE" if code == 0 else "PARTIAL",
                    "outcome": "PASS" if code == 0 else "FAIL",
                    "exit_code": code,
                }
            elif layer == "hosted":
                code = command(
                    c,
                    layer,
                    [
                        sys.executable,
                        "scripts/check_wompi_hosted.py",
                        "--run-dir",
                        str(root / "hosted"),
                        "--cloudflared",
                        str(args.cloudflared),
                        "--execute-sandbox",
                    ],
                    timeout=360,
                    env=env,
                )
                evidence = root / "hosted/evidence.json"
                c["layers"][layer] = (
                    json.loads(evidence.read_text())
                    if evidence.exists()
                    else {"execution": "PARTIAL", "outcome": "FAIL", "exit_code": code}
                )
            elif layer == "remote":
                code = command(
                    c,
                    layer,
                    [
                        sys.executable,
                        "scripts/check_wompi_sandbox.py",
                        "--run-dir",
                        str(root / "remote"),
                        "--execute-sandbox",
                        "--edge-cases",
                    ],
                    timeout=240,
                    env=env,
                )
                evidence = root / "remote/evidence.json"
                c["layers"][layer] = (
                    json.loads(evidence.read_text())
                    if evidence.exists()
                    else {"execution": "PARTIAL", "outcome": "FAIL", "exit_code": code}
                )
    except Exception as exc:
        c["runner_error"] = type(exc).__name__
    finally:
        if started:
            code = command(
                c,
                "postgres-stop",
                ["pg_ctl", "-D", str(root / "pgdata"), "-m", "fast", "-w", "stop"],
                env=env,
            )
            c["postgres_stopped"] = code == 0
        c["end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        c["exit_code"] = (
            0
            if "runner_error" not in c
            and len(c["layers"]) == len(layers)
            and all(v["outcome"] == "PASS" for v in c["layers"].values())
            else 1
        )
        (root / "summary.json").write_text(json.dumps(c, indent=2) + "\n")
        print(json.dumps(c, indent=2))
    return c["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
