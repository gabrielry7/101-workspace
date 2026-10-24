from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

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

    return engine


def init_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        future=True,
    )


CORE_TABLES = frozenset({
    "restaurant_commerce_profiles",
    "restaurant_customers",
    "restaurant_orders",
    "restaurant_payments",
    "restaurant_reservations",
    "restaurant_idempotency_records",
    "restaurant_event_outbox",
    "restaurant_webhook_receipts",
})


def database_ready(engine: Engine, *, require_schema: bool = True) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        if require_schema:
            tables = set(inspect(engine).get_table_names())
            if not CORE_TABLES.issubset(tables):
                return False
        return True
    except Exception:
        return False
