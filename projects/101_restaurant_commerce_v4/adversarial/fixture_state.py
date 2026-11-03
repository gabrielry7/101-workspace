"""Restore disposable business inputs after destructive generated staff requests."""

import sys
from contextlib import contextmanager

from load_contract import validate_target


@contextmanager
def business_inputs(config, config_path):
    validate_target(config, config_path)
    sys.path.insert(0, config["installed"])
    from sqlalchemy import create_engine, delete, select, update
    from world_model.restaurant_commerce.models import (
        ItemStock,
        Menu,
        MenuCategory,
        MenuItem,
        PickupPolicy,
        RestaurantCommerceProfile,
    )

    engine = create_engine(config["database_url"])
    profile = RestaurantCommerceProfile.__table__
    policy = PickupPolicy.__table__
    stock = ItemStock.__table__
    item = MenuItem.__table__
    businesses = config["business_ids"]
    with engine.connect() as conn:
        profiles = list(
            conn.execute(select(profile).where(profile.c.business_id.in_(businesses))).mappings()
        )
        policies = list(
            conn.execute(select(policy).where(policy.c.business_id.in_(businesses))).mappings()
        )
        ids = list(
            conn.scalars(
                select(MenuItem.id)
                .join(MenuCategory)
                .join(Menu)
                .where(Menu.business_id.in_(businesses))
            )
        )
        stocks = list(conn.execute(select(stock).where(stock.c.item_id.in_(ids))).mappings())
        items = list(conn.execute(select(item).where(item.c.id.in_(ids))).mappings())
    try:
        yield
    finally:
        # Only captured synthetic configuration; preserve all attack/order/audit evidence.
        with engine.begin() as conn:
            for row in profiles:
                conn.execute(
                    update(profile)
                    .where(profile.c.business_id == row["business_id"])
                    .values(**dict(row))
                )
            conn.execute(delete(policy).where(policy.c.business_id.in_(businesses)))
            if policies:
                conn.execute(policy.insert(), [dict(row) for row in policies])
            conn.execute(delete(stock).where(stock.c.item_id.in_(ids)))
            if stocks:
                conn.execute(stock.insert(), [dict(row) for row in stocks])
            for row in items:
                conn.execute(update(item).where(item.c.id == row["id"]).values(**dict(row)))
        engine.dispose()
