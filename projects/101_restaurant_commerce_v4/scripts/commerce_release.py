#!/usr/bin/env python3
"""Hash-locked local release bundles, health-gated activation and compatible rollback.

No remote deployment or provisioning. Requires Linux/CPython3.12 for the checked lock.
"""

import argparse
import fcntl
import hashlib
import json
import os
import platform
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment"))
from runtime import config, private_dir, sync_dir, write_json  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(directory, expected, *, bundle_only=False):
    directory = Path(directory)
    if digest(directory / "manifest.json") != expected:
        raise ValueError("Manifest digest mismatch")
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("format") != 1:
        raise ValueError("Unsupported bundle format")
    for name, checksum in manifest["files"].items():
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or not p.parts:
            raise ValueError("Unsafe bundle path")
        target = directory / p
        if any(x.is_symlink() for x in [target, *target.parents]) or digest(target) != checksum:
            raise ValueError("Bundle file mismatch")
    if bundle_only:
        expected_files = set(manifest["files"]) | {"manifest.json"}
        actual_files = {
            str(p.relative_to(directory))
            for p in directory.rglob("*")
            if p.is_file() or p.is_symlink()
        }
        if actual_files != expected_files or any(p.is_symlink() for p in directory.rglob("*")):
            raise ValueError("Unexpected bundle content")
        if (directory / "venv").exists():
            raise ValueError("Bundle must not contain an existing environment")
    return manifest


def pack(wheel, wheelhouse, output, revision):
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    deps = output / "wheels"
    deps.mkdir()
    lock = (ROOT / "deployment/requirements.lock").read_text()
    for line in lock.splitlines():
        if not line or line.startswith("#"):
            continue
        spec, hasharg = line.split()
        name, version = spec.split("==")
        candidates = list(Path(wheelhouse).glob(name.replace("-", "_") + "-" + version + "-*.whl"))
        if len(candidates) != 1 or digest(candidates[0]) != hasharg.split(":", 1)[1]:
            raise ValueError("Missing or mismatched dependency wheel")
        shutil.copy2(candidates[0], deps / candidates[0].name)
    wheel = Path(wheel)
    with zipfile.ZipFile(wheel) as archive:
        metadata = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Invalid application wheel")
        import email

        info = email.message_from_bytes(archive.read(metadata[0]))
        if info["Name"] != "world-model-restaurant-commerce":
            raise ValueError("Wrong application")
    shutil.copy2(wheel, deps / wheel.name)
    lock += (
        "world-model-restaurant-commerce=="
        + info["Version"]
        + " --hash=sha256:"
        + digest(wheel)
        + "\n"
    )
    (output / "requirements.lock").write_text(lock)
    for name in ["runtime.py", "database.py"]:
        shutil.copy2(ROOT / "deployment" / name, output / name)
    files = {
        str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    manifest = {
        "format": 1,
        "application_version": info["Version"],
        "source_revision": revision,
        "python_version": list(sys.version_info[:3]),
        "platform": "linux-x86_64",
        "files": files,
    }
    write_json(output / "manifest.json", manifest)
    return digest(output / "manifest.json")


def install(bundle, expected, site):
    manifest = verify(bundle, expected, bundle_only=True)
    if (
        list(sys.version_info[:3]) != manifest["python_version"]
        or sys.platform != "linux"
        or platform.machine() != "x86_64"
    ):
        raise ValueError("Unqualified Python/platform")
    site = private_dir(site)
    releases = private_dir(site / "releases")
    target = releases / expected[:20]
    if target.exists():
        raise ValueError("Release already exists; do not mutate it")
    shutil.copytree(bundle, target)
    subprocess.run(
        [sys.executable, "-m", "venv", str(target / "venv")], check=True, capture_output=True
    )
    python = str(target / "venv/bin/python")
    result = subprocess.run(
        [
            python,
            "-m",
            "pip",
            "--isolated",
            "install",
            "--no-index",
            "--only-binary=:all:",
            "--require-hashes",
            "--find-links",
            str(target / "wheels"),
            "-r",
            str(target / "requirements.lock"),
        ],
        capture_output=True,
    )
    (target / "install.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Offline locked install failed; see private release log")
    subprocess.run([python, "-m", "pip", "check"], check=True, capture_output=True)
    # The trusted controller keeps the inventory OUTSIDE the mutable release.
    receipts = private_dir(site / "receipts")
    write_json(receipts / (target.name + ".json"), inventory(target))
    return target.name


def inventory(target):
    records = {}
    for p in target.rglob("*"):
        name = str(p.relative_to(target))
        if p.is_symlink():
            records[name] = {"link": os.readlink(p)}
        elif p.is_file():
            records[name] = {"sha256": digest(p)}
    return records


def check_release(site, release):
    if not re_full(release):
        raise ValueError("Invalid release ID")
    target = site / "releases" / release
    if target.is_symlink():
        raise ValueError("Release directory must not be a symlink")
    manifest_hash = digest(target / "manifest.json")
    if not manifest_hash.startswith(release):
        raise ValueError("Release identity mismatch")
    verify(target, manifest_hash)
    receipt = site / "receipts" / (release + ".json")
    if receipt.is_symlink():
        raise ValueError("Trusted install receipt must not be a symlink")
    recorded = json.loads(receipt.read_text())
    if inventory(target) != recorded:
        raise ValueError("Installed tree changed")
    return target


def re_full(value):
    import re

    return re.fullmatch("[a-f0-9]{20}", value)


def ticks(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def terminate(record):
    for p in record.get("processes", []):
        if ticks(p["pid"]) != p["ticks"]:
            continue
        try:
            os.killpg(p["pid"], signal.SIGTERM)
        except ProcessLookupError:
            continue
        end = time.monotonic() + 10
        while ticks(p["pid"]) == p["ticks"] and time.monotonic() < end:
            try:
                waited, _ = os.waitpid(p["pid"], os.WNOHANG)
                if waited:
                    break
            except ChildProcessError:
                pass
            time.sleep(0.05)
        if ticks(p["pid"]) == p["ticks"]:
            try:
                os.killpg(p["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 5
            while ticks(p["pid"]) == p["ticks"] and time.monotonic() < deadline:
                try:
                    os.waitpid(p["pid"], os.WNOHANG)
                except ChildProcessError:
                    pass
                time.sleep(0.05)
            if ticks(p["pid"]) == p["ticks"]:
                raise RuntimeError("Owned process has not exited")


def launch(site, release, config_path, port):
    target = check_release(site, release)
    data = config(config_path)
    record = {
        "release": release,
        "config": str(Path(config_path).resolve()),
        "port": port,
        "processes": [],
    }
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        for role in ["serve", "recover", "monitor"]:
            if role == "recover" and not data["allow_writes"]:
                continue
            gate_read, gate_write = os.pipe()
            try:
                with (site / (role + ".log")).open("ab") as stream:
                    process = subprocess.Popen(
                        [
                            str(target / "venv/bin/python"),
                            "-I",
                            "-B",
                            str(target / "runtime.py"),
                            role,
                            "--config",
                            record["config"],
                            "--release",
                            release,
                            "--port",
                            str(port),
                            "--startup-fd",
                            str(gate_read),
                        ],
                        stdout=stream,
                        stderr=stream,
                        env=env,
                        cwd=target,
                        start_new_session=True,
                        pass_fds=(gate_read,),
                    )
                record["processes"].append(
                    {"role": role, "pid": process.pid, "ticks": ticks(process.pid)}
                )
                write_json(site / "pending.json", record)
                os.write(gate_write, b"1")
            finally:
                os.close(gate_read)
                os.close(gate_write)
            if role == "serve":
                ready = False
                for _ in range(150):
                    if process.poll() is not None:
                        break
                    try:
                        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                        with opener.open(f"http://127.0.0.1:{port}/deployment", timeout=1) as r:
                            identity = json.load(r)
                        with opener.open(f"http://127.0.0.1:{port}/ready", timeout=1) as r:
                            status = r.status
                        if (
                            identity["release"] == release
                            and identity.get("pid") == process.pid
                            and status == 200
                        ):
                            ready = True
                            break
                    except Exception:
                        pass
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("Candidate readiness failed")
            elif role == "recover":
                ready = False
                for _ in range(100):
                    if process.poll() is not None:
                        break
                    try:
                        h = json.loads((Path(data["state_dir"]) / "recovery.json").read_text())
                        if (
                            h["release"] == release
                            and h["pid"] == process.pid
                            and all(s["ok"] for s in h["stages"].values())
                        ):
                            ready = True
                            break
                    except (OSError, ValueError, KeyError):
                        pass
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("Recovery worker did not complete a cycle")
            elif role == "monitor":
                ready = False
                for _ in range(150):
                    if process.poll() is not None:
                        break
                    try:
                        status = json.loads((Path(data["state_dir"]) / "status.json").read_text())
                        if status["monitor_pid"] == process.pid:
                            ready = True
                            break
                    except (OSError, ValueError, KeyError):
                        pass
                    time.sleep(0.1)
                if not ready:
                    raise RuntimeError("Monitor did not complete a cycle")
        return record
    except Exception:
        terminate(record)
        (site / "pending.json").unlink(missing_ok=True)
        raise


def activate(site, release, config_path, port):
    site = private_dir(site)
    check_release(site, release)
    data = config(config_path)
    with (site / "deployment.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pending = site / "pending.json"
        if pending.exists():
            terminate(json.loads(pending.read_text()))
            pending.unlink()
        # Never reread an edited operator config when falling back to the previous release.
        saved_config = private_dir(site / "configs") / (secrets.token_hex(12) + ".json")
        write_json(saved_config, data)
        active = site / "active.json"
        previous = json.loads(active.read_text()) if active.exists() else None
        if previous:
            terminate(previous)
        try:
            record = launch(site, release, saved_config, port)
        except Exception:
            if previous:
                restored = launch(site, previous["release"], previous["config"], previous["port"])
                write_json(active, restored)
                pending.unlink(missing_ok=True)
            raise
        link = site / "next"
        link.unlink(missing_ok=True)
        link.symlink_to(Path("releases") / release)
        os.replace(link, site / "current")
        sync_dir(site)
        if previous:
            write_json(site / "previous.json", {"release": previous["release"]})
        write_json(active, record)
        pending.unlink(missing_ok=True)
        sync_dir(site)
        return record


def stop(site):
    site = private_dir(site)
    with (site / "deployment.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pending = site / "pending.json"
        if pending.exists():
            terminate(json.loads(pending.read_text()))
            pending.unlink()
        record = json.loads((site / "active.json").read_text())
        terminate(record)
        write_json(site / "stopped.json", {"release": record["release"], "at": time.time()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="action", required=True)
    packer = s.add_parser("pack")
    packer.add_argument("--wheel", required=True)
    packer.add_argument("--wheelhouse", required=True)
    packer.add_argument("--output", required=True)
    packer.add_argument("--revision", required=True)
    installer = s.add_parser("install")
    installer.add_argument("--bundle", required=True)
    installer.add_argument("--manifest-sha256", required=True)
    installer.add_argument("--site", required=True)
    for name in ["activate", "rollback"]:
        sub = s.add_parser(name)
        sub.add_argument("--site", required=True)
        sub.add_argument("--config", required=True)
        sub.add_argument("--port", required=True, type=int)
        if name == "activate":
            sub.add_argument("--release", required=True)
    stopper = s.add_parser("stop")
    stopper.add_argument("--site", required=True)
    a = p.parse_args()
    if a.action == "pack":
        print(json.dumps({"manifest_sha256": pack(a.wheel, a.wheelhouse, a.output, a.revision)}))
    elif a.action == "install":
        print(json.dumps({"release": install(a.bundle, a.manifest_sha256, a.site)}))
    elif a.action == "stop":
        stop(a.site)
    else:
        site = private_dir(a.site)
        release = (
            a.release
            if a.action == "activate"
            else json.loads((site / "previous.json").read_text())["release"]
        )
        record = activate(site, release, a.config, a.port)
        print(json.dumps({"release": record["release"], "port": a.port, "status": "ready"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_class": type(exc).__name__, "status": "failed"}), file=sys.stderr)
        raise SystemExit(1) from None
