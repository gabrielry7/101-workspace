"""Explicit offline maintenance; never changes an existing database on app startup."""

import argparse
import os

from .db import make_engine
from .migrations import upgrade_payment_durability


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["upgrade-payments"])
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
        upgrade_payment_durability(engine)
    finally:
        engine.dispose()
    print(
        "Payment durability schema upgraded. Historical orders were not backfilled into payment intents."
    )


if __name__ == "__main__":
    main()
