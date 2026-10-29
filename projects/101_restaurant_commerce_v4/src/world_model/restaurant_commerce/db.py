from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .migrations import (
    CUSTOMER_SAFETY_COLUMNS,
    PAYMENT_DURABILITY_TABLES,
    payment_durability_columns_present,
)
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
        raise RuntimeError(
            "Commerce schema requires an explicit offline upgrade before startup"
        )
    Base.metadata.create_all(engine)
    if not database_ready(engine):
        raise RuntimeError(
            "Commerce schema requires an explicit offline upgrade before startup"
        )


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
)


def database_ready(engine: Engine, *, require_schema: bool = True) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if require_schema:
                inspector = inspect(connection)
                tables = set(inspector.get_table_names())
                if not CORE_TABLES.issubset(tables):
                    return False
                for table, columns in CUSTOMER_SAFETY_COLUMNS.items():
                    if not set(columns).issubset(
                        {c["name"] for c in inspector.get_columns(table)}
                    ):
                        return False
                if not payment_durability_columns_present(connection):
                    return False
        return True
    except (SQLAlchemyError, OSError):
        return False
