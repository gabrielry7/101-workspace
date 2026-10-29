"""M3b offline schema upgrades preserve populated M3a databases."""

import pytest
from sqlalchemy import inspect
from world_model.restaurant_commerce.db import database_ready, init_schema, make_engine
from world_model.restaurant_commerce.migrations import (
    FINANCIAL_TABLES,
    upgrade_financial_resolution,
)
from world_model.restaurant_commerce.models import Base


def test_offline_m3b_upgrade_is_additive_and_repeatable(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    Base.metadata.create_all(
        engine, tables=[t for t in Base.metadata.sorted_tables if t.name not in FINANCIAL_TABLES]
    )
    assert not database_ready(engine)
    with pytest.raises(RuntimeError):
        init_schema(engine)
    upgrade_financial_resolution(engine)
    assert database_ready(engine)
    upgrade_financial_resolution(engine)
    assert FINANCIAL_TABLES.issubset(inspect(engine).get_table_names())
    engine.dispose()


def test_financial_upgrade_refuses_incomplete_schema(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'partial.db'}")
    Base.metadata.create_all(
        engine, tables=[t for t in Base.metadata.sorted_tables if t.name not in FINANCIAL_TABLES]
    )
    with engine.begin() as c:
        c.exec_driver_sql("CREATE TABLE restaurant_financial_operations (id TEXT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="Incomplete"):
        upgrade_financial_resolution(engine)
    assert "restaurant_financial_audit" not in inspect(engine).get_table_names()
    engine.dispose()
