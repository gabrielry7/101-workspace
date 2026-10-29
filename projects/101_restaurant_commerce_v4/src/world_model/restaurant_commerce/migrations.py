"""Explicit offline commerce upgrades; never invoked by application startup.

Back up first and stop application/worker writers. M2's historical column upgrade
is SQLite-only. M3 adds payment durability tables to an already upgraded M2 schema
on SQLite or PostgreSQL; it never invents intents for historical payment rows.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

CUSTOMER_SAFETY_COLUMNS = {
    "restaurant_customers": {
        "whatsapp_verified_at": "DATETIME",
        "marketing_verified_at": "DATETIME",
    },
    "restaurant_orders": {
        "customer_snapshot_json": "TEXT",
        "access_token_version": "INTEGER NOT NULL DEFAULT 0",
    },
    "restaurant_reservations": {"customer_snapshot_json": "TEXT"},
}

PAYMENT_DURABILITY_TABLES = frozenset(
    {
        "restaurant_payment_intents",
        "restaurant_payment_reconciliations",
        "restaurant_payment_notification_inbox",
    }
)


def upgrade_customer_safety(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            "M2 upgrade is verified only on offline SQLite; PostgreSQL migration requires M3"
        )
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table, columns in CUSTOMER_SAFETY_COLUMNS.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, declaration in columns.items():
                if column not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
                    )
    # Do not fabricate historical contact/consent authority. Legacy snapshots stay NULL.


def payment_durability_columns_present(connection: Connection) -> bool:
    """Fail closed for missing or partial M3 tables, including nullable fields used by code."""
    from .models import Base

    inspector = inspect(connection)
    present = set(inspector.get_table_names())
    if not PAYMENT_DURABILITY_TABLES.issubset(present):
        return False
    for name in PAYMENT_DURABILITY_TABLES:
        expected = Base.metadata.tables.get(name)
        if expected is None or not set(expected.columns.keys()).issubset(
            {column["name"] for column in inspector.get_columns(name)}
        ):
            return False
    return True


def upgrade_payment_durability(engine: Engine) -> None:
    """Atomically add M3 tables to an offline M2 database without backfilling authority.

    The caller must have backed up the database and stopped writers. Existing
    incomplete M3 tables are rejected, not guessed at or destructively replaced.
    Repeating a completed upgrade is safe. No provider calls are made.
    """
    from .models import Base

    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RuntimeError(
            "Payment durability upgrade supports SQLite and PostgreSQL only"
        )
    if not PAYMENT_DURABILITY_TABLES.issubset(Base.metadata.tables):
        raise RuntimeError("Payment durability models are unavailable")
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            # sqlite3 legacy mode does not BEGIN for DDL. Without this explicit
            # transaction, a failed second CREATE TABLE leaves the first committed.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        inspector = inspect(connection)
        present = set(inspector.get_table_names())
        required = set(CUSTOMER_SAFETY_COLUMNS) | {"restaurant_payments"}
        if not required.issubset(present):
            raise RuntimeError("M3 requires an existing M2 commerce schema")
        for table, columns in CUSTOMER_SAFETY_COLUMNS.items():
            if not set(columns).issubset(
                {column["name"] for column in inspector.get_columns(table)}
            ):
                raise RuntimeError(
                    "M3 requires the explicit M2 customer-safety upgrade first"
                )
        for name in PAYMENT_DURABILITY_TABLES & present:
            if not set(Base.metadata.tables[name].columns.keys()).issubset(
                {column["name"] for column in inspector.get_columns(name)}
            ):
                raise RuntimeError(
                    "Existing M3 table is incomplete; restore or repair offline"
                )
        for table in Base.metadata.sorted_tables:
            if table.name in PAYMENT_DURABILITY_TABLES:
                table.create(connection, checkfirst=True)
        if not payment_durability_columns_present(connection):
            raise RuntimeError("Payment durability schema verification failed")


FINANCIAL_TABLES = frozenset({"restaurant_financial_operations", "restaurant_financial_audit", "restaurant_loyalty_refund_debts"})


def financial_columns_present(connection):
    from .models import Base
    inspector = inspect(connection)
    present = set(inspector.get_table_names())
    return FINANCIAL_TABLES.issubset(present) and all(
        set(Base.metadata.tables[name].columns.keys()).issubset(
            {c["name"] for c in inspector.get_columns(name)}) for name in FINANCIAL_TABLES)


def upgrade_financial_resolution(engine):
    """Explicit additive M3a -> M3b upgrade; preserves all historical state."""
    from .models import Base
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RuntimeError("Financial upgrade supports SQLite and PostgreSQL only")
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        if not payment_durability_columns_present(connection):
            raise RuntimeError("M3b requires the completed M3a offline upgrade")
        inspector = inspect(connection)
        for name in FINANCIAL_TABLES & set(inspector.get_table_names()):
            if not set(Base.metadata.tables[name].columns.keys()).issubset(
                {c["name"] for c in inspector.get_columns(name)}):
                raise RuntimeError("Incomplete financial schema; restore or repair offline")
        for table in Base.metadata.sorted_tables:
            if table.name in FINANCIAL_TABLES:
                table.create(connection, checkfirst=True)
        if not financial_columns_present(connection):
            raise RuntimeError("Financial schema verification failed")


STAFF_TABLES = frozenset({"restaurant_staff_accounts", "restaurant_staff_memberships", "restaurant_staff_sessions", "restaurant_staff_login_windows", "restaurant_staff_audit"})


def staff_columns_present(connection):
    from .models import Base
    inspector = inspect(connection)
    present = set(inspector.get_table_names())
    return STAFF_TABLES.issubset(present) and all(
        set(Base.metadata.tables[name].columns.keys()).issubset(
            {c["name"] for c in inspector.get_columns(name)}) for name in STAFF_TABLES)


def upgrade_staff(engine):
    """Offline additive M3b -> M4 upgrade. No implicit staff or memberships."""
    from .models import Base
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RuntimeError("Staff upgrade supports SQLite and PostgreSQL only")
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        if not financial_columns_present(connection) or not payment_durability_columns_present(connection):
            raise RuntimeError("M4 requires completed M3b schema")
        inspector = inspect(connection)
        for name in STAFF_TABLES & set(inspector.get_table_names()):
            if not set(Base.metadata.tables[name].columns.keys()).issubset(
                {c["name"] for c in inspector.get_columns(name)}):
                raise RuntimeError("Incomplete staff schema; restore or repair offline")
        for table in Base.metadata.sorted_tables:
            if table.name in STAFF_TABLES:
                table.create(connection, checkfirst=True)
        if not staff_columns_present(connection):
            raise RuntimeError("Staff schema verification failed")
