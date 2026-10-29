"""Bounded native scanner execution against disposable loopback commerce only.

No model calls, production credentials, container engine mutation or global install.
All native outputs and command receipts are retained, including unsuccessful runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

TOOLCHAIN = Path(os.environ.get("COMMERCE_TOOLCHAIN", "/tmp/101-commerce-toolchain"))


def utc():
    return dt.datetime.now(dt.UTC).isoformat()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=str) + "\n")


def redact_native(value, secrets):
    """Preserve native schema while removing ephemeral synthetic capabilities."""
    if isinstance(value, dict):
        return {k: redact_native(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_native(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "<redacted-synthetic-token>")
        return re.sub(r"v2\.[0-9]+\.[0-9a-f]{64}", "<redacted-order-capability>", value)
    return value


def fetch(url, data=None, headers=None, timeout=15):
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            result = json.loads(raw)
        except ValueError:
            result = raw.decode(errors="replace")
        return exc.code, result


class Recorder:
    def __init__(self, output, config):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.rows = []

    def run(self, name, command, timeout=180, env=None, cwd=None):
        row = {
            "layer": name,
            "command": command,
            "started_at": utc(),
            "target": self.config.get("base_url"),
            "revision": self.config.get("revision"),
            "wheel_sha256": self.config.get("wheel_sha256"),
            "cwd": str(cwd or Path.cwd()),
        }
        with (self.output / (name + ".log")).open("w") as log:
            try:
                p = subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
                row["exit_code"] = p.returncode
            except subprocess.TimeoutExpired:
                row["exit_code"] = 124
                row["error"] = "bounded process timeout"
            except OSError as exc:
                row["exit_code"] = 127
                row["error"] = str(exc)
        row["ended_at"] = utc()
        self.rows.append(row)
        self.save()
        return row

    def save(self):
        dump(self.output / "commands.json", self.rows)


def bootstrap(rec, layers):
    """Pinned public tool downloads, task-owned destinations, recorded checksums."""
    TOOLCHAIN.mkdir(parents=True, exist_ok=True)
    if "semgrep" in layers and not (TOOLCHAIN / "semgrep-venv/bin/semgrep").exists():
        row = rec.run(
            "bootstrap-semgrep-venv",
            ["uv", "venv", "--python", "3.12", str(TOOLCHAIN / "semgrep-venv")],
            120,
        )
        if row["exit_code"] == 0:
            rec.run(
                "bootstrap-semgrep",
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(TOOLCHAIN / "semgrep-venv/bin/python"),
                    "semgrep==1.182.1",
                ],
                240,
            )
    assets = []
    if "trivy" in layers and not (TOOLCHAIN / "trivy/trivy").exists():
        assets.append(
            (
                "trivy",
                "https://github.com/aquasecurity/trivy/releases/download/v0.76.1/trivy_0.76.1_Linux-64bit.tar.gz",
                "c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0",
                "tar",
            )
        )
    if "zap" in layers:
        if not list(TOOLCHAIN.glob("zap/*/zap-*.jar")):
            assets.append(
                (
                    "zap",
                    "https://github.com/zaproxy/zaproxy/releases/download/v2.17.0/ZAP_2.17.0_Crossplatform.zip",
                    "94c8f767b1c2e94f0db66b3ae56514d5e3f5a728ee1b6c798e0c8fe2d61fbff0",
                    "zip",
                )
            )
        if not list(TOOLCHAIN.glob("java/*/bin/java")):
            assets.append(
                (
                    "java",
                    "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.21%2B9/OpenJDK17U-jre_x64_linux_hotspot_17.0.21_9.tar.gz",
                    "9f41bf88c7900c7097444a1bdeb84146ae692bc08842490ab098063c74bf9a8a",
                    "tar",
                )
            )
    for name, url, digest, kind in assets:
        row = {
            "layer": "bootstrap-" + name,
            "command": ["download-and-verify", url, digest],
            "started_at": utc(),
        }
        destination = TOOLCHAIN / (name + ".download")
        target = TOOLCHAIN / name
        try:
            urllib.request.urlretrieve(url, destination)
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual != digest:
                raise ValueError("download checksum mismatch")
            target.mkdir(exist_ok=True)
            if kind == "tar":
                with tarfile.open(destination) as archive:
                    archive.extractall(target, filter="data")
            else:
                with zipfile.ZipFile(destination) as archive:
                    archive.extractall(target)
            row.update(exit_code=0, sha256=actual)
            destination.unlink()  # Only this run's verified download archive.
        except Exception as exc:  # noqa: BLE001 - record layer failure and continue independent scans
            row.update(exit_code=1, error=str(exc))
        row["ended_at"] = utc()
        rec.rows.append(row)
        rec.save()


def semgrep(rec, source):
    binary = TOOLCHAIN / "semgrep-venv/bin/semgrep"
    env = {
        **os.environ,
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
    }
    inventory = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (source / "src").rglob("*")
        if p.is_file() and p.suffix in {".py", ".js", ".html"}
    }
    dump(rec.output / "semgrep-source-inventory.json", inventory)
    rec.run("semgrep-version", [str(binary), "--version"], 30, env)
    report = rec.output / "semgrep.json"
    run = rec.run(
        "semgrep-source",
        [
            str(binary),
            "scan",
            "--config",
            "p/python",
            "--config",
            "p/javascript",
            "--config",
            "p/security-audit",
            "--metrics",
            "off",
            "--disable-version-check",
            "--json",
            "--output",
            str(report),
            str(source / "src"),
        ],
        180,
        env,
        cwd=source,
    )
    if not report.exists():
        return {
            "execution": "BLOCKED",
            "outcome": "UNASSESSED",
            "blocker": run.get("error", "No native report; see log"),
        }
    data = json.loads(report.read_text())
    findings = data.get("results", [])
    errors = data.get("errors", [])
    scanned = len(data.get("paths", {}).get("scanned", []))
    return {
        "execution": "COMPLETE"
        if run["exit_code"] == 0 and not errors and scanned
        else "PARTIAL",
        "outcome": "FAIL"
        if findings
        else ("PASS" if not errors and run["exit_code"] == 0 else "UNASSESSED"),
        "native_findings": len(findings),
        "native_errors": len(errors),
        "files_scanned": scanned,
        "findings": [
            {
                "rule": x["check_id"],
                "path": x["path"],
                "line": x["start"]["line"],
                "severity": x["extra"]["severity"],
            }
            for x in findings
        ],
        "coverage_gaps": [
            "Community Edition intrafile analysis; no claim of authenticated business-logic verification."
        ],
    }


def trivy(rec, source, config):
    binary = TOOLCHAIN / "trivy/trivy"
    cache = Path(
        os.environ.get(
            "COMMERCE_TRIVY_CACHE",
            config.get("trivy_cache", str(TOOLCHAIN / "trivy-cache")),
        )
    )
    rec.run("trivy-version", [str(binary), "--version"], 30)
    runs = {}
    for layer, scanners, target in [("source", "secret,misconfig", source)]:
        report = rec.output / ("trivy-" + layer + ".json")
        row = rec.run(
            "trivy-" + layer,
            [
                str(binary),
                "filesystem",
                "--cache-dir",
                str(cache),
                "--scanners",
                scanners,
                "--format",
                "json",
                "--output",
                str(report),
                "--timeout",
                "5m",
                "--skip-dirs",
                ".git",
                "--skip-dirs",
                "build",
                "--skip-dirs",
                ".venv",
                str(target),
            ],
            330,
        )
        runs[layer] = trivy_result(report, row)
    deps = rec.output / "installed-dependencies"
    deps.mkdir(exist_ok=True)
    freeze = rec.run(
        "runtime-pip-freeze",
        [config.get("python", "python"), "-m", "pip", "freeze", "--exclude-editable"],
        45,
    )
    shutil.copyfile(rec.output / "runtime-pip-freeze.log", deps / "requirements.txt")
    report = rec.output / "trivy-dependencies.json"
    row = rec.run(
        "trivy-dependencies",
        [
            str(binary),
            "filesystem",
            "--cache-dir",
            str(cache),
            "--scanners",
            "vuln",
            "--list-all-pkgs",
            "--format",
            "json",
            "--output",
            str(report),
            "--timeout",
            "5m",
            str(deps),
        ],
        330,
    )
    runs["dependencies"] = trivy_result(report, row)
    if freeze["exit_code"] != 0 or runs["dependencies"].get("packages", 0) == 0:
        runs["dependencies"].update(
            execution="PARTIAL",
            outcome="UNASSESSED",
            blocker="Runtime dependency inventory failed or no installed packages were analyzed.",
        )
    image = config.get("container_image_archive")
    if image:
        report = rec.output / "trivy-container.json"
        row = rec.run(
            "trivy-container",
            [
                str(binary),
                "image",
                "--input",
                image,
                "--cache-dir",
                str(cache),
                "--scanners",
                "vuln,secret,misconfig",
                "--format",
                "json",
                "--output",
                str(report),
                "--timeout",
                "5m",
            ],
            330,
        )
        runs["container"] = trivy_result(report, row)
    else:
        rec.run("docker-runtime-probe", ["docker", "version"], 15)
        rec.run("podman-runtime-probe", ["podman", "version"], 15)
        runs["container"] = {
            "execution": "BLOCKED",
            "outcome": "UNASSESSED",
            "blocker": "No built application container archive supplied; runtime availability recorded below. Filesystem scan is not container scan.",
            "runtime_paths": {
                name: shutil.which(name) for name in ["docker", "podman", "buildah"]
            },
        }
    return runs


def trivy_result(report, row):
    if not report.exists():
        return {
            "execution": "BLOCKED",
            "outcome": "UNASSESSED",
            "exit_code": row["exit_code"],
            "blocker": "No completed native report; inspect command log.",
        }
    data = json.loads(report.read_text())
    results = data.get("Results", [])
    findings = {
        k: sum(len(x.get(k, []) or []) for x in results)
        for k in ["Vulnerabilities", "Secrets", "Misconfigurations"]
    }
    count = sum(findings.values())
    return {
        "execution": "COMPLETE" if row["exit_code"] == 0 else "PARTIAL",
        "outcome": "FAIL"
        if count
        else ("PASS" if row["exit_code"] == 0 and results else "UNASSESSED"),
        "counts": findings,
        "targets": len(results),
        "packages": sum(len(x.get("Packages", []) or []) for x in results),
        "native_report": report.name,
        "coverage_gaps": [
            "No finding targets/recognized configuration manifests in native report; zero findings does not establish configuration coverage. Secret scanning ran over the requested source tree, but native output supplies no clean-file count."
        ]
        if not results
        else [],
    }


def zap_scan(rec, config):
    base = config["base_url"].rstrip("/")
    host = urllib.parse.urlsplit(base).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("ZAP refuses non-loopback target")
    java = next(TOOLCHAIN.glob("java/*/bin/java"), None)
    jar = next(TOOLCHAIN.glob("zap/*/zap-*.jar"), None)
    if not java or not jar:
        return {
            "execution": "BLOCKED",
            "outcome": "UNASSESSED",
            "blocker": "Portable Java/ZAP artifact absent",
        }
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    home = rec.output / "zap-home"
    home.mkdir(exist_ok=True)
    command = [
        str(java),
        "-Xmx512m",
        "-jar",
        str(jar),
        "-daemon",
        "-silent",
        "-host",
        "127.0.0.1",
        "-port",
        str(port),
        "-dir",
        str(home),
        "-config",
        "api.disablekey=true",
        "-config",
        "api.addrs.addr.name=127.0.0.1",
        "-config",
        "api.addrs.addr.regex=false",
        "-config",
        "autoupdate.checkOnStart=false",
        "-config",
        "autoupdate.downloadNewRelease=false",
        "-config",
        "connection.timeoutInSecs=5",
    ]
    api_base = f"http://127.0.0.1:{port}"
    calls = []

    def api(component, kind, operation, **kwargs):
        url = (
            f"{api_base}/JSON/{component}/{kind}/{operation}/?"
            + urllib.parse.urlencode(kwargs)
        )
        status, result = fetch(url, timeout=30)
        # Do not persist synthetic auth tokens in command receipts.
        safe = {
            k: ("<redacted>" if k in {"replacement", "request"} else v)
            for k, v in kwargs.items()
        }
        calls.append(
            {
                "time": utc(),
                "component": component,
                "operation": operation,
                "params": safe,
                "status": status,
                "result": result
                if operation not in {"messages", "sendRequest"}
                else "<native messages retained separately>",
            }
        )
        if status != 200 or isinstance(result, dict) and "code" in result:
            raise RuntimeError(f"ZAP {component}/{operation}: {status} {result}")
        return result

    row = {
        "layer": "zap-active",
        "command": command,
        "started_at": utc(),
        "target": base,
        "revision": config.get("revision"),
        "wheel_sha256": config.get("wheel_sha256"),
    }
    rec.rows.append(row)
    rec.save()
    log = (rec.output / "zap-daemon.log").open("w")
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    result = {
        "execution": "PARTIAL",
        "outcome": "UNASSESSED",
        "coverage_gaps": [
            "Global staff token only; no real staff principals or customer login exist. Customer capability token is exercised.",
            "Bounded low-strength active scan; not exhaustive penetration testing.",
        ],
    }
    try:
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("ZAP exited during startup")
            try:
                version = api("core", "view", "version")
                break
            except (OSError, RuntimeError):
                time.sleep(0.5)
        else:
            raise RuntimeError("ZAP startup timeout")
        result["version"] = version
        context = api(
            "context", "action", "newContext", contextName="commerce-disposable"
        )["contextId"]
        api(
            "context",
            "action",
            "includeInContext",
            contextName="commerce-disposable",
            regex=re.escape(base) + r"(?:/.*)?",
        )
        api(
            "context",
            "action",
            "setContextInScope",
            contextName="commerce-disposable",
            booleanInScope="true",
        )
        api("core", "action", "setMode", mode="standard")
        token = config["operator_token"]
        api(
            "replacer",
            "action",
            "addRule",
            description="synthetic-operator",
            enabled="true",
            matchType="REQ_HEADER",
            matchRegex="false",
            matchString="X-101-Operator-Token",
            replacement=token,
            url=re.escape(base) + r"/.*",
        )
        business = config["business_ids"][0]
        status, store = fetch(base + f"/api/restaurants/{business}/storefront")
        assert status == 200
        items = [
            i
            for m in store["menus"]
            for c in m["categories"]
            for i in c["items"]
            if i["available"] and not i["modifier_groups"]
        ]
        body = {
            "customer": {"name": "ZAP Synthetic", "phone": "3007770001"},
            "items": [{"menu_item_id": items[0]["id"], "quantity": 1}],
            "payment_provider": store["payment_provider"],
            "idempotency_key": "zap-" + uuid.uuid4().hex,
        }
        status, order = fetch(base + f"/api/restaurants/{business}/orders", body)
        assert status == 200, (status, order)
        customer_token = order["access_token"]
        api(
            "replacer",
            "action",
            "addRule",
            description="synthetic-order",
            enabled="true",
            matchType="REQ_HEADER",
            matchRegex="false",
            matchString="X-101-Order-Token",
            replacement=customer_token,
            url=re.escape(base) + r"/api/orders/" + re.escape(order["id"]) + r".*",
        )
        seeds = [
            "/",
            "/admin",
            "/delivery",
            "/growth",
            f"/api/restaurants/{business}/storefront",
            f"/api/operator/restaurants/{business}/orders",
            "/api/orders/" + order["id"],
        ]
        reached = []
        for path in seeds:
            raw = f"GET {path} HTTP/1.1\r\nHost: {urllib.parse.urlsplit(base).netloc}\r\n\r\n"
            response = api(
                "core", "action", "sendRequest", request=raw, followRedirects="false"
            )
            for message in response.get("sendRequest", []):
                reached.append(
                    {
                        "path": path,
                        "response_status": message.get("responseHeader", "").split(
                            "\r\n"
                        )[0],
                    }
                )
        dump(rec.output / "zap-auth-reached.json", reached)
        if not any(
            "/api/operator/" in r["path"] and "200" in r["response_status"]
            for r in reached
        ):
            raise RuntimeError("No authenticated staff200 reached")
        if not any(
            "/api/orders/" in r["path"] and "200" in r["response_status"]
            for r in reached
        ):
            raise RuntimeError("No authenticated customer capability200 reached")
        # Import the actual live contract. Native importer result is retained.
        result["openapi_import"] = api(
            "openapi",
            "action",
            "importUrl",
            url=base + "/openapi.json",
            hostOverride=base,
            contextId=context,
        )
        api("ascan", "action", "setOptionThreadPerHost", Integer=2)
        api("ascan", "action", "setOptionMaxRuleDurationInMins", Integer=1)
        api("ascan", "action", "setOptionMaxScanDurationInMins", Integer=5)

        for policy in api("ascan", "view", "policies").get("policies", []):
            api(
                "ascan",
                "action",
                "setPolicyAttackStrength",
                id=policy["id"],
                attackStrength="LOW",
            )
        result["context"] = api(
            "context", "view", "context", contextName="commerce-disposable"
        )
        scanners = api("ascan", "view", "scanners").get("scanners", [])
        external_rules = [
            x["id"]
            for x in scanners
            if any(
                word in x.get("name", "").lower()
                for word in [
                    "out of band",
                    "oast",
                    "ssrf",
                    "server side request forgery",
                    "log4shell",
                    "xml external entity",
                    "external redirect",
                ]
            )
        ]
        selected = [
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
        api("ascan", "action", "disableAllScanners")
        api("ascan", "action", "enableScanners", ids=",".join(selected))
        result["selected_http_rule_ids"] = selected
        result["disabled_external_callback_rules"] = external_rules
        result["coverage_gaps"].append(
            "Focused HTTP rule set: DOM browser rules, external callbacks, unrelated database engines and other rule families excluded; exact IDs retained."
        )
        focus_customer = config.get("zap_focus_customer", False)
        scan_url = base + ("/api/orders/" + order["id"] if focus_customer else "/")
        result["scan_url"] = scan_url
        result["focus_customer"] = focus_customer
        scan = api(
            "ascan",
            "action",
            "scan",
            url=scan_url,
            recurse="false" if focus_customer else "true",
            inScopeOnly="true",
            contextId=context,
        )["scan"]
        result["scan_id"] = scan
        scan_started = time.monotonic()
        deadline = scan_started + 360
        while time.monotonic() < deadline:
            state = api("ascan", "view", "status", scanId=scan)
            if state.get("status") == "100":
                break
            time.sleep(2)
        else:
            raise RuntimeError(
                "Active scan did not complete within360s; no success claim"
            )
        result["scan_status"] = 100
        result["active_seconds"] = time.monotonic() - scan_started
        result["budget_exhausted"] = result["active_seconds"] >= 295
        ids = api("ascan", "view", "messagesIds", scanId=scan)
        dump(rec.output / "zap-active-message-ids.json", ids)
        total = int(
            api("core", "view", "numberOfMessages", baseurl=base)["numberOfMessages"]
        )
        messages = {"messages": []}
        headers = []
        for offset in range(0, min(total, 10000), 100):
            batch = api(
                "core", "view", "messages", baseurl=base, start=offset, count=100
            ).get("messages", [])
            headers.extend(
                {
                    key: msg.get(key)
                    for key in ["id", "requestHeader", "responseHeader", "rtt"]
                }
                for msg in batch
            )
            if offset < 2000:
                messages["messages"].extend(batch)
        result["total_http_history_messages"] = total
        result["history_export_limit"] = 2000
        result["header_export_limit"] = 10000
        result["exported_header_count"] = len(headers)
        result["protected_counts_are_lower_bounds"] = len(headers) < total
        dump(
            rec.output / "zap-all-message-headers.json",
            redact_native(headers, [token, customer_token]),
        )
        dump(
            rec.output / "zap-messages.json",
            redact_native(messages, [token, customer_token]),
        )
        alerts = api("core", "view", "alerts", baseurl=base, start=0, count=10000)
        dump(
            rec.output / "zap-alerts.json",
            redact_native(alerts, [token, customer_token]),
        )
        count = len(ids.get("messagesIds", []))
        result["active_request_count"] = count
        active_ids = {str(x) for x in ids.get("messagesIds", [])}
        active_messages = [m for m in headers if str(m.get("id")) in active_ids]
        result["active_protected_success_counts"] = {
            kind: sum(
                needle in m.get("requestHeader", "").split("\r\n")[0]
                and " 200 " in m.get("responseHeader", "").split("\r\n")[0]
                for m in active_messages
            )
            for kind, needle in [
                ("staff", "/api/operator/"),
                ("customer", "/api/orders/"),
            ]
        }
        dump(
            rec.output / "zap-active-progress.json",
            api("ascan", "view", "scanProgress", scanId=scan),
        )
        result["alerts"] = len(alerts.get("alerts", []))
        result["http_messages"] = len(messages.get("messages", []))
        result["execution"] = (
            "COMPLETE" if count > 0 and not result["budget_exhausted"] else "PARTIAL"
        )
        result["outcome"] = (
            "FAIL" if result["alerts"] else ("PASS" if count > 0 else "UNASSESSED")
        )
    except Exception as exc:  # noqa: BLE001 - record layer failure and continue independent scans
        result["blocker"] = str(exc)
    finally:
        try:
            api("core", "action", "shutdown")
        except Exception as exc:  # noqa: BLE001 - owned process termination below is authoritative
            calls.append({"operation": "shutdown", "error": str(exc)})
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        row["exit_code"] = proc.returncode
        row["ended_at"] = utc()
        rec.save()
        log.close()
        dump(
            rec.output / "zap-api-calls.json",
            redact_native(
                calls, [config.get("operator_token"), locals().get("customer_token")]
            ),
        )
    if (rec.output / "INTERRUPTED.json").exists():
        result.update(json.loads((rec.output / "INTERRUPTED.json").read_text()))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--layers", default="semgrep,trivy,zap")
    args = p.parse_args()
    config = json.loads(Path(args.config).read_text())
    source = Path(config["source_path"]).resolve()
    if not (source / "src/world_model/restaurant_commerce/api.py").exists():
        raise ValueError("Not the commerce source directory")
    recorder = Recorder(args.output, config)
    summary = {}
    bootstrap(recorder, args.layers.split(","))
    for layer in args.layers.split(","):
        try:
            if layer == "semgrep":
                summary[layer] = semgrep(recorder, source)
            elif layer == "trivy":
                summary[layer] = trivy(recorder, source, config)
            elif layer == "zap":
                summary[layer] = zap_scan(recorder, config)
        except Exception as exc:  # noqa: BLE001 - record layer failure and continue independent scans
            summary[layer] = {
                "execution": "BLOCKED",
                "outcome": "UNASSESSED",
                "blocker": str(exc),
            }
        dump(recorder.output / "summary.json", summary)
    summary["strix"] = {
        "execution": "BLOCKED",
        "outcome": "UNASSESSED",
        "blocker": "No authorized model budget/config supplied. No model call made; do not claim a completed assessment.",
        "docker_runtime": shutil.which("docker"),
        "strix_executable": shutil.which("strix"),
    }
    dump(recorder.output / "summary.json", summary)
    print(json.dumps(summary, indent=2))

    def incomplete(value):
        if isinstance(value, dict):
            if "execution" in value and (
                value["execution"] != "COMPLETE" or value.get("outcome") != "PASS"
            ):
                return True
            return any(incomplete(v) for v in value.values())
        return False

    raise SystemExit(1 if incomplete(summary) else 0)


if __name__ == "__main__":
    main()
