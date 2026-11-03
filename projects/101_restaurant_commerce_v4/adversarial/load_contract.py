"""Safety and financial acceptance rules for actual native load runs."""

from pathlib import Path
from urllib.parse import urlsplit


def validate_target(config, path):
    root = Path(config["run_dir"]).resolve()
    if Path(path).resolve() != root / "config.json" or not (root / ".commerce-test-run").is_file():
        raise ValueError("Owned disposable config required")
    for name in ("base_url", "provider_direct_url", "database_url"):
        if urlsplit(config[name]).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Only loopback test services are allowed")


def accepted(counts, audit, users, code):
    completed = counts.get("completed_checkouts", 0)
    return bool(
        code == 0
        and completed > 0
        and counts.get("peak_users", 0) >= users
        and counts.get("failures", 1) == 0
        and audit["duplicate_intents"] == 0
        and completed
        == audit["orders"]
        == audit["paid_orders"]
        == audit["payments"]
        == audit["provider_effects"]
    )


def validate_profiles(profiles):
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("At least one load profile required")
    names = set()
    for row in profiles:
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            raise ValueError("Profile must contain name/users/spawn/duration")
        name, users, spawn, seconds = row
        if (
            not isinstance(name, str)
            or not name.isalnum()
            or name in names
            or any(type(value) is not int for value in (users, spawn, seconds))
            or not (1 <= users <= 1000 and 1 <= spawn <= 100 and 10 <= seconds <= 1800)
            or users / spawn >= seconds
        ):
            raise ValueError("Invalid bounded local load profile")
        names.add(name)
    if sum(row[3] + 30 for row in profiles) > 1700:
        raise ValueError("Profiles exceed outer layer execution budget")
