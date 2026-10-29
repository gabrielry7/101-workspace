"""Offline M3 migration proofs on disposable SQLite and opt-in local PostgreSQL schemas.

Set COMMERCE_MIGRATION_TEST_DATABASE_URL to the disposable loopback PostgreSQL URL
for the same cases on PostgreSQL. Each case owns and drops a unique schema only.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from world_model.restaurant_commerce.db import (
    database_ready,
    init_schema,
    make_engine,
    session_factory,
)
from world_model.restaurant_commerce.migrations import (
    PAYMENT_DURABILITY_TABLES,
    upgrade_payment_durability,
)
from world_model.restaurant_commerce.models import Base, Customer, Order, Payment
from world_model.restaurant_commerce.seed import seed_demo

POSTGRES_URL = os.environ.get("COMMERCE_MIGRATION_TEST_DATABASE_URL")
DIALECTS = ["sqlite"] + (["postgresql"] if POSTGRES_URL else [])


@pytest.fixture(params=DIALECTS)
def legacy_engine(request, tmp_path):
    admin = None
    schema = None
    if request.param == "postgresql":
        url = make_url(POSTGRES_URL)
        assert url.get_backend_name() == "postgresql"
        assert url.host in {"localhost", "127.0.0.1", "::1"}, (
            "Disposable loopback PostgreSQL only"
        )
        schema = "commerce_m3_test_" + uuid4().hex
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    else:
        engine = make_engine("sqlite:///" + str(tmp_path / "legacy.db"))
    try:
        # Reconstruct the pre-M3 schema, rather than creating new tables then
        # pretending an empty database proves an existing-data migration.
        Base.metadata.create_all(
            engine,
            tables=[
                table
                for table in Base.metadata.sorted_tables
                if table.name not in PAYMENT_DURABILITY_TABLES
            ],
        )
        with session_factory(engine)() as session:
            business = seed_demo(session)
            customer = Customer(
                business_id=business, phone="3005550700", name="Historical synthetic"
            )
            session.add(customer)
            session.flush()
            order = Order(
                id="historical-order",
                public_code="OLEGACYM3",
                business_id=business,
                customer_id=customer.id,
                customer_snapshot_json='{"name":"Retained contact"}',
                status="awaiting_payment",
                fulfillment_type="pickup",
                payment_status="pending",
                currency="COP",
                subtotal_minor=1000,
                total_minor=1000,
                prep_minutes=10,
                idempotency_key="historical-intent-key",
            )
            session.add(order)
            session.flush()
            session.add(
                Payment(
                    id="historical-payment",
                    order_id=order.id,
                    provider="simulated",
                    provider_reference="retained-provider-reference",
                    status="pending",
                    amount_minor=1000,
                    currency="COP",
                )
            )
            session.commit()
        yield engine
    finally:
        engine.dispose()
        if admin is not None:
            try:
                with admin.begin() as connection:
                    connection.execute(DropSchema(schema, cascade=True))
            finally:
                admin.dispose()


def retained_rows(engine):
    with engine.connect() as connection:
        return (
            dict(connection.execute(select(Order.__table__)).mappings().one()),
            dict(connection.execute(select(Payment.__table__)).mappings().one()),
        )


def test_existing_database_requires_explicit_m3_upgrade(legacy_engine):
    before = retained_rows(legacy_engine)
    assert not database_ready(legacy_engine)
    assert database_ready(legacy_engine, require_schema=False)
    with pytest.raises(RuntimeError, match="explicit offline upgrade"):
        init_schema(legacy_engine)
    assert not PAYMENT_DURABILITY_TABLES.intersection(
        inspect(legacy_engine).get_table_names()
    )
    assert retained_rows(legacy_engine) == before


def test_upgrade_preserves_rows_and_is_repeatable_without_fabricating_intents(
    legacy_engine,
):
    before = retained_rows(legacy_engine)
    upgrade_payment_durability(legacy_engine)
    upgrade_payment_durability(legacy_engine)
    assert database_ready(legacy_engine)
    assert retained_rows(legacy_engine) == before
    with legacy_engine.connect() as connection:
        for name in PAYMENT_DURABILITY_TABLES:
            assert connection.execute(select(Base.metadata.tables[name])).all() == []


def test_failed_upgrade_rolls_back_created_tables_and_preserves_rows(legacy_engine):
    before = retained_rows(legacy_engine)
    tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name in PAYMENT_DURABILITY_TABLES
    ]

    def fail_second_create(*_args, **_kwargs):
        raise RuntimeError("synthetic DDL interruption")

    event.listen(tables[1], "before_create", fail_second_create)
    try:
        with pytest.raises(RuntimeError, match="synthetic DDL interruption"):
            upgrade_payment_durability(legacy_engine)
    finally:
        event.remove(tables[1], "before_create", fail_second_create)
    assert not PAYMENT_DURABILITY_TABLES.intersection(
        inspect(legacy_engine).get_table_names()
    )
    assert retained_rows(legacy_engine) == before
    upgrade_payment_durability(legacy_engine)
    assert database_ready(legacy_engine)


def test_missing_m2_columns_fail_before_m3_changes(legacy_engine):
    with legacy_engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE restaurant_orders DROP COLUMN customer_snapshot_json")
        )
    with pytest.raises(RuntimeError, match="M2 customer-safety upgrade first"):
        upgrade_payment_durability(legacy_engine)
    assert not PAYMENT_DURABILITY_TABLES.intersection(
        inspect(legacy_engine).get_table_names()
    )
    assert not database_ready(legacy_engine)


def test_incomplete_m3_table_is_not_silently_accepted(legacy_engine):
    Table(
        "restaurant_payment_intents",
        MetaData(),
        Column("id", String(36), primary_key=True),
    ).create(legacy_engine)
    before = set(inspect(legacy_engine).get_table_names())
    with pytest.raises(RuntimeError, match="incomplete"):
        upgrade_payment_durability(legacy_engine)
    assert set(inspect(legacy_engine).get_table_names()) == before
    assert not database_ready(legacy_engine)


def test_readiness_detects_missing_required_m3_column(legacy_engine):
    upgrade_payment_durability(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE restaurant_payment_intents DROP COLUMN lease_token")
        )
    assert not database_ready(legacy_engine)
    with pytest.raises(RuntimeError, match="incomplete"):
        upgrade_payment_durability(legacy_engine)
