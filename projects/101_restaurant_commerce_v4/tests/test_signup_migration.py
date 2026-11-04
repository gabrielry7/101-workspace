"""Populated legacy customer/order migration, with data and FK preservation."""
import pytest
from sqlalchemy import inspect, select, func, text
from test_payment_durability_m3 import factory, request
from world_model.restaurant_commerce.customer_signup_migrations import upgrade_signup, ready
from world_model.restaurant_commerce.customer_signup_models import TABLES
from world_model.restaurant_commerce.models import Customer, Order, Base
from world_model.restaurant_commerce.db import make_engine, init_schema, session_factory
from world_model.restaurant_commerce.seed import seed_demo, DEMO_BUSINESS_ID
from world_model.restaurant_commerce.service import RestaurantCommerceService


def test_legacy_sqlite_customer_migration_preserves_orders_indexes_and_rows(tmp_path):
    engine=make_engine('sqlite:///'+str(tmp_path/'legacy.db'))
    column=Customer.__table__.c.phone
    column.nullable=False
    try:init_schema(engine)
    finally:column.nullable=True
    sessions=session_factory(engine)
    with sessions() as s:
        seed_demo(s);service=RestaurantCommerceService(s);order=service.create_order(DEMO_BUSINESS_ID,request(service))
        oid=order.id;cid=s.get(Order,oid).customer_id
        before=s.scalar(select(func.count()).select_from(Customer))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in TABLES:table.drop(engine)
    assert not ready(engine)
    upgrade_signup(engine);upgrade_signup(engine)
    assert ready(engine)
    with sessions() as s:
        assert s.get(Order,oid).customer_id==cid
        assert s.scalar(select(func.count()).select_from(Customer))==before
        assert s.execute(text('PRAGMA foreign_key_check')).all()==[]
        s.add(Customer(business_id=DEMO_BUSINESS_ID,phone=None,email='first@example.test'))
        s.add(Customer(business_id=DEMO_BUSINESS_ID,phone=None,email='second@example.test'));s.commit()
    assert 'uq_restaurant_customer_business_phone' in {x['name'] for x in inspect(engine).get_unique_constraints('restaurant_customers')}
    assert 'ix_restaurant_customers_business_last_order' in {x['name'] for x in inspect(engine).get_indexes('restaurant_customers')}
    engine.dispose()


def test_migration_on_current_database_is_idempotent(factory):
    engine=factory.kw['bind']
    with factory() as s:before=s.scalar(select(func.count()).select_from(Customer))
    if engine.dialect.name=='postgresql':
        with engine.begin() as c:c.exec_driver_sql('ALTER TABLE restaurant_customers ALTER COLUMN phone SET NOT NULL')
    upgrade_signup(engine);upgrade_signup(engine)
    assert ready(engine)
    with factory() as s:assert s.scalar(select(func.count()).select_from(Customer))==before
