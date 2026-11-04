"""Explicit offline installation of execution history and ledger retention guards."""

from sqlalchemy import inspect, text

from .loyalty_execution_models import EXECUTION_TABLES, IMMUTABLE_EXECUTION_TABLES, LoyaltyPointLot
from .loyalty_migrations import configuration_schema_ready
from .loyalty_models import LOYALTY_TABLES, POSTGRES_PROTECTIONS, SQLITE_PROTECTIONS
from .models import Base, LoyaltyLedgerEntry
from .refunds import PaymentRefund

SQLITE = {}
POSTGRES = {}
for table in (*IMMUTABLE_EXECUTION_TABLES, LoyaltyLedgerEntry.__table__, PaymentRefund.__table__):
    for operation, trigger_type in (("UPDATE", 19), ("DELETE", 11)):
        name = table.name + "_immutable_" + operation.lower()
        SQLITE[name] = (
            f"CREATE TRIGGER {name} BEFORE {operation} ON {table.name} "
            "BEGIN SELECT RAISE(ABORT, 'Immutable loyalty execution history'); END"
        )
        POSTGRES[name] = (
            table.name,
            "BEGIN RAISE EXCEPTION 'Immutable loyalty execution history'; END",
            trigger_type,
        )


# Lot balances are projections; their origin, valuation and original expiry are history.
lot_table = LoyaltyPointLot.__tablename__
lot_name = lot_table + "_origin_update"
origin_columns = (
    "account_id",
    "ledger_id",
    "version_id",
    "order_id",
    "original_points",
    "cost_per_point_minor",
    "redemption_bps",
    "expires_at",
)
sqlite_changed = " OR ".join(f"NEW.{column} IS NOT OLD.{column}" for column in origin_columns)
postgres_changed = " OR ".join(
    f"NEW.{column} IS DISTINCT FROM OLD.{column}" for column in origin_columns
)
SQLITE[lot_name] = (
    f"CREATE TRIGGER {lot_name} BEFORE UPDATE ON {lot_table} "
    f"BEGIN SELECT CASE WHEN {sqlite_changed} THEN RAISE(ABORT, 'Immutable lot origin') END; END"
)
POSTGRES[lot_name] = (
    lot_table,
    f"BEGIN IF {postgres_changed} THEN RAISE EXCEPTION 'Immutable lot origin'; "
    "END IF; RETURN NEW; END",
    19,
)

lot_delete_name = lot_table + "_origin_delete"
SQLITE[lot_delete_name] = (
    f"CREATE TRIGGER {lot_delete_name} BEFORE DELETE ON {lot_table} "
    "BEGIN SELECT RAISE(ABORT, 'Immutable lot origin'); END"
)
POSTGRES[lot_delete_name] = (lot_table, "BEGIN RAISE EXCEPTION 'Immutable lot origin'; END", 11)


def execution_schema_ready(connection, *, required=False, known_tables=None):
    return configuration_schema_ready(
        connection,
        required=required,
        known_tables=known_tables,
        tables=EXECUTION_TABLES,
        sqlite_protections=SQLITE,
        postgres_protections=POSTGRES,
    )


def loyalty_schema_ready(connection, *, required=False, known_tables):
    """One bulk reflection/guard query for all installed optional loyalty stages."""
    from .loyalty_assignment_migrations import (
        SQLITE as assignment_sqlite,
        POSTGRES as assignment_postgres,
    )
    from .loyalty_assignment_models import ASSIGNMENT_TABLES

    has_assignment = bool(set(known_tables) & ASSIGNMENT_TABLES)
    if not set(known_tables) & EXECUTION_TABLES and not has_assignment:
        return configuration_schema_ready(connection, required=required, known_tables=known_tables)
    return configuration_schema_ready(
        connection,
        required=True,
        known_tables=known_tables,
        tables=LOYALTY_TABLES | EXECUTION_TABLES | (ASSIGNMENT_TABLES if has_assignment else set()),
        sqlite_protections={
            **SQLITE_PROTECTIONS,
            **SQLITE,
            **(assignment_sqlite if has_assignment else {}),
        },
        postgres_protections={
            **POSTGRES_PROTECTIONS,
            **POSTGRES,
            **(assignment_postgres if has_assignment else {}),
        },
    )


def installed(session):
    # Uses the caller transaction/search_path; never cache across schema changes.
    return inspect(session.connection()).has_table("restaurant_loyalty_order_snapshots")


def upgrade_loyalty_execution(engine):
    from .db import database_ready

    if engine.dialect.name not in {"sqlite", "postgresql"} or not database_ready(
        engine, require_loyalty=True
    ):
        raise RuntimeError(
            "Complete configuration upgrade; partial execution schema requires offline repair"
        )
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            conn.execute(text("SELECT pg_advisory_xact_lock(101, 31)"))
        present = set(inspect(conn).get_table_names()) & EXECUTION_TABLES
        if present:
            if not execution_schema_ready(conn, required=True):
                raise RuntimeError("Incomplete execution schema; repair offline")
            return
        Base.metadata.create_all(
            conn, tables=[t for t in Base.metadata.sorted_tables if t.name in EXECUTION_TABLES]
        )
        for name, sql in SQLITE.items():
            if engine.dialect.name == "sqlite":
                conn.exec_driver_sql(sql)
            else:
                table, body, kind = POSTGRES[name]
                operation = "UPDATE" if kind == 19 else "DELETE"
                conn.exec_driver_sql(
                    f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ {body} $$"
                )
                conn.exec_driver_sql(
                    f"CREATE TRIGGER {name} BEFORE {operation} ON {table} "
                    f"FOR EACH ROW EXECUTE FUNCTION {name}()"
                )
        if not execution_schema_ready(conn, required=True):
            raise RuntimeError("Execution schema verification failed")
