"""Explicit offline maintenance; never changes an existing database on app startup."""

import argparse
import os

from .db import make_engine
from .connection_models import upgrade_connections
from .customer_signup_migrations import upgrade_signup
from .loyalty_assignment_migrations import upgrade_loyalty_assignment
from .loyalty_execution_migrations import upgrade_loyalty_execution
from .loyalty_migrations import upgrade_loyalty_configuration
from .migrations import upgrade_payment_durability, upgrade_financial_resolution, upgrade_staff, upgrade_wompi_sandbox, upgrade_operations, upgrade_campaigns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["upgrade-connections", "upgrade-signup", "upgrade-loyalty-assignment", "upgrade-loyalty-execution", "upgrade-loyalty-config", "upgrade-campaigns", "upgrade-payments", "upgrade-finance", "upgrade-staff", "upgrade-wompi-sandbox", "upgrade-operations"])
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
        if args.command == "upgrade-connections":
            upgrade_connections(engine)
        elif args.command == "upgrade-signup":
            upgrade_signup(engine)
        elif args.command == "upgrade-loyalty-assignment":
            upgrade_loyalty_assignment(engine)
        elif args.command == "upgrade-loyalty-execution":
            upgrade_loyalty_execution(engine)
        elif args.command == "upgrade-loyalty-config":
            upgrade_loyalty_configuration(engine)
        elif args.command == "upgrade-campaigns":
            upgrade_campaigns(engine)
        elif args.command == "upgrade-operations":
            upgrade_operations(engine)
        elif args.command == "upgrade-wompi-sandbox":
            upgrade_wompi_sandbox(engine)
        elif args.command == "upgrade-staff":
            upgrade_staff(engine)
        elif args.command == "upgrade-finance":
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
