"""Live PostgreSQL regression for destructive fuzz-profile isolation."""

import json
import os
from pathlib import Path

import pytest
from fixture_state import business_inputs


def test_failed_profile_restores_business_settings():
    path = Path(os.environ["COMMERCE_TEST_CONFIG"])
    config = json.loads(path.read_text())
    # The secondary synthetic business avoids ongoing primary-business traffic.
    config["business_ids"] = [config["business_ids"][1]]
    with pytest.raises(RuntimeError, match="generated failure"):
        with business_inputs(config, path):
            from sqlalchemy import create_engine, select, update
            from world_model.restaurant_commerce.models import RestaurantCommerceProfile

            engine = create_engine(config["database_url"])
            table = RestaurantCommerceProfile.__table__
            with engine.begin() as conn:
                before = dict(
                    conn.execute(
                        select(table).where(table.c.business_id == config["business_ids"][0])
                    )
                    .mappings()
                    .one()
                )
                conn.execute(
                    update(table)
                    .where(table.c.business_id == config["business_ids"][0])
                    .values(ordering_enabled=not before["ordering_enabled"])
                )
            raise RuntimeError("generated failure")
    with engine.connect() as conn:
        after = dict(
            conn.execute(select(table).where(table.c.business_id == config["business_ids"][0]))
            .mappings()
            .one()
        )
    engine.dispose()
    assert after == before
