"""Local trusted administrator tool; never accepts passwords in command arguments."""

import argparse
import getpass
import os

from sqlalchemy import select

from .db import database_ready, make_engine, session_factory
from .models import StaffAccount, StaffAudit, StaffMembership
from .staff import ROLES, password_hash, provision, username


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "create",
            "reset-password",
            "disable",
            "membership",
            "remove-membership",
        ],
    )
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--actor",
        required=True,
        help="Accountability identity of the trusted local administrator",
    )
    parser.add_argument("--business")
    parser.add_argument("--role", choices=sorted(ROLES))
    parser.add_argument(
        "--platform-admin",
        action="store_true",
        help="Explicit global maintenance authority at creation",
    )
    args = parser.parse_args()
    if not 1 <= len(args.actor) <= 36:
        parser.error("Actor must contain 1–36 characters")
    if args.command in {"create", "membership"} and (
        not args.business or not args.role
    ):
        parser.error("Explicit business and role required")
    if args.command == "remove-membership" and not args.business:
        parser.error("Business required")
    if args.platform_admin and args.command != "create":
        parser.error("Platform authority is only granted explicitly at creation")
    url = os.environ.get("COMMERCE_DATABASE_URL")
    if not url:
        parser.error("COMMERCE_DATABASE_URL required")
    engine = make_engine(url)
    try:
        if not database_ready(engine):
            parser.error("Complete offline schema upgrade before staff maintenance")
        with session_factory(engine)() as session:
            secret = None
            if args.command in {"create", "reset-password"}:
                secret = getpass.getpass("New passphrase (15–128 characters): ")
                if secret != getpass.getpass("Confirm passphrase: "):
                    parser.error("Passphrases differ")
            if args.command == "create":
                provision(
                    session,
                    args.username,
                    secret,
                    args.business,
                    args.role,
                    actor=args.actor,
                    platform_admin=args.platform_admin,
                )
            else:
                account = session.scalar(
                    select(StaffAccount)
                    .where(StaffAccount.username == username(args.username))
                    .with_for_update()
                )
                if not account:
                    parser.error("Account not found")
                if args.command == "reset-password":
                    account.password_hash = password_hash(secret)
                    account.auth_version += 1
                elif args.command == "disable":
                    account.active = False
                    account.auth_version += 1
                else:
                    membership = session.get(
                        StaffMembership, (account.id, args.business)
                    )
                    if args.command == "remove-membership":
                        if membership:
                            session.delete(membership)
                    elif membership:
                        membership.role = args.role
                    else:
                        session.add(
                            StaffMembership(
                                account_id=account.id,
                                business_id=args.business,
                                role=args.role,
                            )
                        )
                session.add(
                    StaffAudit(
                        actor_id=args.actor,
                        business_id=args.business,
                        action="staff." + args.command,
                        resource=account.id,
                    )
                )
                session.commit()
    finally:
        engine.dispose()
    print("Staff maintenance committed; no credentials printed.")


if __name__ == "__main__":
    main()
