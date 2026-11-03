"""Readiness remains fail-closed without serial catalogue roundtrips per table."""

from sqlalchemy import event, text
from test_payment_durability_m3 import factory as factory
from world_model.restaurant_commerce.db import database_ready


def test_readiness_bounds_postgres_catalogue_roundtrips(factory):
    engine = factory.kw["bind"]
    statements = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        assert database_ready(engine)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    if engine.dialect.name == "postgresql":
        assert len(statements) <= 10, (
            f"{len(statements)} readiness roundtrips amplify network latency"
        )


def test_readiness_rechecks_required_columns_after_schema_changes(factory):
    engine = factory.kw["bind"]
    assert database_ready(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE restaurant_payment_intents DROP COLUMN last_error"))
    assert not database_ready(engine)
