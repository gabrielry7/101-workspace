from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from . import campaign_models, loyalty_models, refunds  # noqa: F401 - register additive metadata
from .loyalty_execution_migrations import loyalty_schema_ready
from .loyalty_execution_models import EXECUTION_TABLES
from .loyalty_assignment_models import ASSIGNMENT_TABLES
from .loyalty_models import LOYALTY_TABLES
from .loyalty_measurement_models import MEASUREMENT_TABLES
from .migrations import (
    CUSTOMER_SAFETY_COLUMNS,
    FINANCIAL_TABLES,
    OPERATIONS_TABLES,
    PAYMENT_DURABILITY_TABLES,
    STAFF_TABLES,
)
from .customer_signup_models import TABLES as SIGNUP_TABLES
from .connection_models import TABLES as CONNECTION_TABLES
from .models import Base


def make_engine(database_url: str | None = None) -> Engine:
    if database_url is None:
        path = Path("restaurant_commerce.db").resolve()
        database_url = f"sqlite:///{path}"

    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(
        database_url,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=FULL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()

        @event.listens_for(engine, "savepoint")
        def _sqlite_savepoint_outer_transaction(connection, _name):
            # sqlite3 legacy transaction control does not BEGIN for SAVEPOINT.
            # Releasing an outermost savepoint would commit a claim even when the
            # request subsequently rolls back. Preserve the caller's transaction.
            driver = connection.connection.driver_connection
            if not driver.in_transaction:
                connection.exec_driver_sql("BEGIN")

    return engine


def init_schema(engine: Engine) -> None:
    existing = set(inspect(engine).get_table_names())
    if existing.intersection(Base.metadata.tables) and not database_ready(engine):
        raise RuntimeError("Commerce schema requires an explicit offline upgrade before startup")
    # Existing installations opt into sandbox state only through offline maintenance.
    tables = [
        t
        for t in Base.metadata.sorted_tables
        if t.name not in (EXECUTION_TABLES | ASSIGNMENT_TABLES | MEASUREMENT_TABLES)
        and (not existing or t.name not in (SIGNUP_TABLES | CONNECTION_TABLES))
        and (
            not existing
            or t.name
            not in (
                {"restaurant_wompi_sandbox_lookups", "restaurant_wompi_sandbox_discovery"}
                | LOYALTY_TABLES
            )
        )
    ]
    Base.metadata.create_all(engine, tables=tables)
    if not database_ready(engine):
        raise RuntimeError("Commerce schema requires an explicit offline upgrade before startup")


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        future=True,
    )


CORE_TABLES = (
    frozenset(
        {
            "restaurant_commerce_profiles",
            "restaurant_customers",
            "restaurant_orders",
            "restaurant_payments",
            "restaurant_reservations",
            "restaurant_idempotency_records",
            "restaurant_event_outbox",
            "restaurant_webhook_receipts",
        }
    )
    | PAYMENT_DURABILITY_TABLES
    | FINANCIAL_TABLES
    | STAFF_TABLES
    | OPERATIONS_TABLES
    | frozenset(
        t
        for t in Base.metadata.tables
        if t.startswith("restaurant_campaign")
        or t
        in {
            "restaurant_contact_permissions",
            "restaurant_permission_evidence",
            "restaurant_payment_refunds",
        }
    )
)


def database_ready(
    engine: Engine,
    *,
    require_schema: bool = True,
    require_loyalty: bool = False,
    require_measurement: bool = False,
    deadline: float | None = None,
) -> bool:
    try:
        with engine.connect() as connection:
            if deadline is not None:

                def before_query(*_args):
                    if time.monotonic() >= deadline:
                        raise SQLAlchemyError("Readiness deadline exceeded")

                # Connection-local listener: no global event/pool mutation. Closed
                # Connection objects and their listeners are not reused by the pool.
                event.listen(connection, "before_cursor_execute", before_query)
                before_query()
                if connection.dialect.name == "postgresql":
                    budget_ms = max(1, int((deadline - time.monotonic()) * 1000))
                    connection.execute(
                        text(
                            "SELECT set_config('statement_timeout', :budget, true), "
                            "set_config('lock_timeout', :budget, true)"
                        ),
                        {"budget": str(budget_ms)},
                    )
            connection.execute(text("SELECT 1"))
            if require_schema:
                inspector = inspect(connection)
                tables = set(inspector.get_table_names())
                from .loyalty_measurement_migrations import measurement_schema_ready
                if not measurement_schema_ready(connection, required=require_measurement, known_tables=tables):
                    return False
                if not loyalty_schema_ready(
                    connection, required=require_loyalty, known_tables=tables
                ):
                    return False
                if not CORE_TABLES.issubset(tables):
                    return False
                expected = {
                    table: set(columns) for table, columns in CUSTOMER_SAFETY_COLUMNS.items()
                }
                for table in (
                    PAYMENT_DURABILITY_TABLES | FINANCIAL_TABLES | STAFF_TABLES | OPERATIONS_TABLES
                ):
                    expected[table] = set(Base.metadata.tables[table].columns.keys())
                # One fresh bulk reflection preserves every existing required-column
                # check without a network roundtrip for every table/helper.
                reflected = inspector.get_multi_columns(filter_names=sorted(expected))
                if any(
                    not columns.issubset(
                        {column["name"] for column in reflected.get((None, table), [])}
                    )
                    for table, columns in expected.items()
                ):
                    return False

        return True
    except (SQLAlchemyError, OSError):
        return False
