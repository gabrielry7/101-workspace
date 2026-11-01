"""Private PostgreSQL logical backups and non-destructive quarantined restores.

Archive and manifest are sensitive. They are not committed or printed. This is
not WAL/PITR, encrypted offsite storage, secret backup or provider reconciliation.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import config, database_id, engine_for, sync_dir, utc, write_json  # noqa: E402


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(data):
    return database_id(data)


def signing_id(data):
    return hashlib.sha256(data["public_access_secret"].encode()).hexdigest()


def pg_env(data):
    from sqlalchemy.engine import make_url

    url = make_url(data["database_url"])
    # Neither URI nor password appears in process arguments or command receipts.
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "PGHOST": url.host,
        "PGPORT": str(url.port or 5432),
        "PGDATABASE": url.database,
        "PGUSER": url.username or os.environ.get("USER", ""),
        "PGPASSWORD": url.password or "",
        "PGCONNECT_TIMEOUT": "5",
        "PGOPTIONS": "-c statement_timeout=60000",
    }


def run_pg(command, data):
    result = subprocess.run(command, env=pg_env(data), capture_output=True, timeout=120)
    if result.returncode:
        # Native stderr can include private DB names, data or authentication details.
        raise RuntimeError("PostgreSQL backup/restore command failed")
    return result


def backup(data, directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = utc()
    partial = directory / "database.partial"
    archive = directory / "database.dump"
    try:
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        run_pg(
            ["pg_dump", "--format=custom", "--no-owner", "--no-privileges", "--file", str(partial)],
            data,
        )
        with partial.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(partial, archive)
        sync_dir(directory)
        manifest = {
            "format": 1,
            "kind": "postgresql-custom-logical",
            "started_at": started,
            "completed_at": utc(),
            "source_id": identity(data),
            "signing_secret_sha256": signing_id(data),
            "archive_sha256": sha(archive),
            "archive_bytes": archive.stat().st_size,
            "pg_dump_version": subprocess.check_output(["pg_dump", "--version"], text=True).strip(),
            "rpo_note": (
                "Snapshot lies within recorded interval; "
                "later writes and remote effects are not included"
            ),
            "scope": (
                "One database only; roles, deployment config, "
                "event spool and provider history are separate"
            ),
        }
        write_json(directory / "manifest.json", manifest)
        write_json(
            Path(data["state_dir"]) / "backup.json",
            {
                "completed_at": manifest["completed_at"],
                "database_id": identity(data),
                "manifest_sha256": sha(directory / "manifest.json"),
                "archive_sha256": manifest["archive_sha256"],
            },
        )
        return {
            "manifest_sha256": sha(directory / "manifest.json"),
            "bytes": manifest["archive_bytes"],
        }
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def restore(data, directory, manifest_sha, expected_database, offline=False):
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from world_model.restaurant_commerce.db import database_ready

    if not offline or data["allow_writes"]:
        raise ValueError("Restore requires offline quarantine configuration")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", expected_database or ""):
        raise ValueError("Unsafe target database name")
    if make_url(data["database_url"]).database != expected_database:
        raise ValueError("Target database confirmation mismatch")
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    archive = directory / "database.dump"
    for path in [directory, manifest_path, archive]:
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("Backup paths must be private and not symlinks")
    if sha(manifest_path) != manifest_sha:
        raise ValueError("Backup manifest digest mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format") != 1 or sha(archive) != manifest["archive_sha256"]:
        raise ValueError("Backup archive integrity failed")
    if manifest["source_id"] == identity(data):
        raise ValueError("Restore into a different, fresh database only")
    if manifest["signing_secret_sha256"] != signing_id(data):
        raise ValueError("Signing configuration does not match; recovery capabilities would change")
    engine = engine_for(data)
    started = time.monotonic()
    try:
        with engine.connect() as conn:
            # Keep this advisory lock until pg_restore commits. Cooperating tools
            # cannot race a second restore; no --clean or destructive down migration.
            if not conn.scalar(text("SELECT pg_try_advisory_lock(1016001)")):
                raise ValueError("Restore already in progress")
            objects = conn.scalar(
                text(
                    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
                    "AND n.nspname NOT LIKE 'pg_toast%' "
                    "AND c.relkind IN ('r','p','v','m','S','f')"
                )
            )
            if objects:
                raise ValueError("Target database is not empty")
            run_pg(
                [
                    "pg_restore",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-privileges",
                    "--dbname",
                    expected_database,
                    str(archive),
                ],
                data,
            )
        ready = database_ready(engine)
        receipt = {
            "at": utc(),
            "manifest_sha256": manifest_sha,
            "source_id": manifest["source_id"],
            "target_id": identity(data),
            "database_schema_ready": ready,
            "quarantine": True,
            "restore_seconds": round(time.monotonic() - started, 3),
            "release_gate": (
                "Verify identity, revocations and post-snapshot/provider gap before enabling writes"
            ),
        }
        write_json(Path(data["state_dir"]) / "restore.json", receipt)
        return receipt
    finally:
        engine.dispose()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["backup", "restore"])
    p.add_argument("--config", required=True)
    p.add_argument("--directory", required=True)
    p.add_argument("--manifest-sha256")
    p.add_argument("--expected-database")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    data = config(args.config)
    if args.command == "backup":
        result = backup(data, args.directory)
    else:
        result = restore(
            data, args.directory, args.manifest_sha256, args.expected_database, args.offline
        )
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_class": type(exc).__name__, "status": "failed"}), file=sys.stderr)
        raise SystemExit(1) from None
