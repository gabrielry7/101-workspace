"""Explicit offline SQLite M2 upgrade; never run by application startup.

Back up first, stop writers, then call upgrade_customer_safety(engine).
PostgreSQL migrations and locking proof belong to M3; this is not that proof.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

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
