"""Explicit offline maintenance; never changes an existing database on app startup."""

import argparse
import os

from .db import make_engine
from .migrations import upgrade_payment_durability, upgrade_financial_resolution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["upgrade-payments", "upgrade-finance"])
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Confirm all writers are stopped and a backup exists",
    )
    args = parser.parse_args()
    if not args.offline:
        parser.error(
            "Stop writers and back up the database, then explicitly pass --offline"
        )
    url = os.environ.get("COMMERCE_DATABASE_URL")
    if not url:
        parser.error(
            "COMMERCE_DATABASE_URL is required; credentials are read from the environment"
        )
    engine = make_engine(url)
    try:
        if args.command == "upgrade-finance":
            upgrade_financial_resolution(engine)
        else:
            upgrade_payment_durability(engine)
    finally:
        engine.dispose()
    print(
        "Requested schema upgrade completed. Historical financial authority was not fabricated."
    )


if __name__ == "__main__":
    main()
