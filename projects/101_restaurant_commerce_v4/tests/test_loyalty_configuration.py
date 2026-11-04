"""Stage-one acceptance: historical rules, scope, migration and optimistic conflicts."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as SchemaError
from sqlalchemy import delete, inspect, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from staff_helpers import staff_headers
from test_payment_durability_m3 import factory as shared_factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import (
    database_ready,
    init_schema,
)
from world_model.restaurant_commerce.errors import (
    ConcurrencyConflictError,
    NotFoundError,
    ValidationError,
)
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_migrations import upgrade_loyalty_configuration
from world_model.restaurant_commerce.loyalty_models import (
    IMMUTABLE_TABLES,
    LOYALTY_TABLES,
    POSTGRES_PROTECTIONS,
    LoyaltyConfigurationAudit,
    LoyaltyExperimentVariant,
    LoyaltyExperimentVersion,
    LoyaltyStrategyVersion,
)
from world_model.restaurant_commerce.loyalty_schemas import (
    ExperimentCreate,
    ExperimentDocument,
    Publish,
    StrategyCreate,
    StrategyDocument,
    StrategyEdit,
    Transition,
)
from world_model.restaurant_commerce.models import (
    Base,
    Customer,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    RestaurantCommerceProfile,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID

factory = shared_factory


def document(**changes):
    return StrategyDocument.model_validate(
        {
            "name": "Incremental points",
            "currency": "COP",
            "earning": {"type": "points", "spend_minor_per_point": 1000},
            "maximum_reward_minor": 10000,
            "per_customer_budget_minor": 50000,
            "campaign_budget_minor": 1000000,
            **changes,
        }
    )


def create(service, key="one", **changes):
    return service.create(
        "programs", BID, StrategyCreate(request_key=key, document=document(**changes))
    )


def publish(service, draft, kind="programs"):
    return service.publish(
        kind, BID, draft["id"], Publish(expected_revision=draft["revision"], digest=draft["digest"])
    )


def experiment(version_id, **changes):
    now = datetime.now(UTC)
    return ExperimentDocument.model_validate(
        {
            "name": "Incremental pilot",
            "currency": "COP",
            "enrollment_start": now,
            "enrollment_end": now + timedelta(days=30),
            "exclusion_group": "loyalty",
            "analysis_plan": "Fixed 60-day follow-up, all randomized customers; no winner.",
            "variants": [
                {"name": "Control", "allocation_bps": 5000},
                {"name": "Points", "allocation_bps": 5000, "strategy_version_id": version_id},
            ],
            **changes,
        }
    )


def test_publish_edit_and_retry_preserve_original_version(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        draft = create(service)
        version = publish(service, draft)
        assert publish(service, draft) == version
        current = service.get("programs", BID, draft["id"])
        changed = service.edit(
            "programs",
            BID,
            draft["id"],
            StrategyEdit(
                expected_revision=current["revision"], document=document(name="New proposal")
            ),
        )
        next_version = publish(service, changed)
        assert version["version_id"] != next_version["version_id"]
        old = session.get(LoyaltyStrategyVersion, version["version_id"])
        assert json.loads(old.document)["name"] == "Incremental points"
        assert len(service.get("programs", BID, draft["id"])["versions"]) == 2
        assert create(service)["id"] == draft["id"]
        with pytest.raises(ConcurrencyConflictError):
            create(service, name="different initial request")
        assert len(session.scalars(select(LoyaltyConfigurationAudit)).all()) == 4


def test_stale_review_and_cross_business_rejected(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        draft = create(service)
        with pytest.raises(NotFoundError):
            service.get("programs", "other", draft["id"])
        with pytest.raises(ConcurrencyConflictError):
            service.publish(
                "programs", BID, draft["id"], Publish(expected_revision=1, digest="0" * 64)
            )
        with pytest.raises(ConcurrencyConflictError):
            service.edit(
                "programs",
                BID,
                draft["id"],
                StrategyEdit(expected_revision=99, document=document()),
            )
        assert not session.scalars(select(LoyaltyStrategyVersion)).all()


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("table_index", range(4))
def test_published_history_and_audit_reject_raw_sql(factory, operation, table_index):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        version = publish(service, create(service))
        exp = service.create(
            "experiments",
            BID,
            ExperimentCreate(request_key="exp", document=experiment(version["version_id"])),
        )
        publish(service, exp, "experiments")
        table = IMMUTABLE_TABLES[table_index]
        with pytest.raises(DBAPIError):
            session.execute(
                update(table).values(id=table.c.id) if operation == "update" else delete(table)
            )
            session.commit()
        session.rollback()
        assert session.execute(select(table)).first() is not None


def test_experiment_pins_published_versions_control_and_currency(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        draft = create(service)
        version = publish(service, draft)
        exp = service.create(
            "experiments",
            BID,
            ExperimentCreate(request_key="exp", document=experiment(version["version_id"])),
        )
        saved = publish(service, exp, "experiments")
        variants = session.scalars(
            select(LoyaltyExperimentVariant).where(
                LoyaltyExperimentVariant.experiment_version_id == saved["version_id"]
            )
        ).all()
        assert sum(v.allocation_bps for v in variants) == 10000
        assert sum(v.strategy_version_id is None for v in variants) == 1
        assert len(session.get(LoyaltyExperimentVersion, saved["version_id"]).random_salt) == 64
        for bad in (draft["id"], "nonexistent"):
            with pytest.raises(ValidationError):
                service.create(
                    "experiments", BID, ExperimentCreate(request_key=bad, document=experiment(bad))
                )
        with pytest.raises(ValidationError):
            service.create(
                "experiments",
                BID,
                ExperimentCreate(
                    request_key="currency",
                    document=experiment(version["version_id"], currency="USD"),
                ),
            )
        session.add(
            RestaurantCommerceProfile(business_id="other", slug="other", display_name="Other")
        )
        session.commit()
        with pytest.raises(ValidationError):
            service.create(
                "experiments",
                "other",
                ExperimentCreate(request_key="scope", document=experiment(version["version_id"])),
            )


def test_database_rejects_cross_business_variant(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        version = publish(service, create(service))
        exp = service.create(
            "experiments",
            BID,
            ExperimentCreate(request_key="exp", document=experiment(version["version_id"])),
        )
        saved = publish(service, exp, "experiments")
        session.add(
            LoyaltyExperimentVariant(
                experiment_version_id=saved["version_id"],
                business_id="other",
                name="Forged",
                allocation_bps=1,
                strategy_version_id=version["version_id"],
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_pause_archive_and_activation_gate(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        draft = create(service)
        publish(service, draft)
        current = service.get("programs", BID, draft["id"])
        with pytest.raises(ValidationError, match="Activation unavailable"):
            service.transition(
                "programs",
                BID,
                draft["id"],
                Transition(expected_revision=current["revision"], state="active"),
            )
        paused = service.transition(
            "programs",
            BID,
            draft["id"],
            Transition(expected_revision=current["revision"], state="paused"),
        )
        archived = service.transition(
            "programs",
            BID,
            draft["id"],
            Transition(expected_revision=paused["revision"], state="archived"),
        )
        assert len(archived["versions"]) == 1
        with pytest.raises(ValidationError):
            service.edit(
                "programs",
                BID,
                draft["id"],
                StrategyEdit(expected_revision=archived["revision"], document=document()),
            )


@pytest.mark.parametrize(
    "changes",
    [
        {"campaign_budget_minor": -1},
        {"campaign_budget_minor": 1.5},
        {"campaign_budget_minor": True},
        {"per_customer_budget_minor": 1000001},
        {"currency": "cop"},
        {"earning": {"type": "arbitrary_python"}},
        {"eligibility": {"included_product_ids": ["x"], "excluded_product_ids": ["x"]}},
        {"start_at": "2026-01-01T00:00:00"},
    ],
)
def test_invalid_configuration(changes):
    with pytest.raises(SchemaError):
        document(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "variants": [
                {"name": "A", "allocation_bps": 5000},
                {"name": "B", "allocation_bps": 5000},
            ]
        },
        {
            "variants": [
                {"name": "A", "allocation_bps": 1},
                {"name": "B", "allocation_bps": 1, "strategy_version_id": "v"},
            ]
        },
        {"baseline_benefits_preserved": False},
        {"allow_overlap": True},
    ],
)
def test_invalid_experiment(changes):
    with pytest.raises(SchemaError):
        experiment("v", **changes)


def test_concurrent_edits_have_one_winner(factory):
    with factory() as session:
        draft = create(LoyaltyConfigurationService(session, "manager"))

    def edit(name):
        with factory() as session:
            try:
                return LoyaltyConfigurationService(session, name).edit(
                    "programs",
                    BID,
                    draft["id"],
                    StrategyEdit(expected_revision=draft["revision"], document=document(name=name)),
                )["document"]["name"]
            except ConcurrencyConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, ["A", "B"]))
    assert results.count("conflict") == 1


def test_upgrade_populated_schema_and_repeat_without_touching_legacy(factory):
    with factory() as session:
        engine = session.get_bind()
        customer = Customer(business_id=BID, phone="3001112233", name="Migration fixture")
        session.add(customer)
        session.flush()
        account = LoyaltyAccount(
            business_id=BID,
            customer_id=customer.id,
            available_points=17,
            lifetime_earned_points=17,
            lifetime_redeemed_points=0,
        )
        session.add(account)
        session.flush()
        session.add(
            LoyaltyLedgerEntry(
                account_id=account.id,
                delta_points=17,
                reason="legacy-fixture",
                idempotency_key="legacy-fixture",
            )
        )
        session.commit()
        before = [tuple(row) for row in session.execute(select(LoyaltyAccount.__table__))]
        ledger = [tuple(row) for row in session.execute(select(LoyaltyLedgerEntry.__table__))]
    # Empty new feature tables only; model the existing installed schema.
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in LOYALTY_TABLES:
                table.drop(connection)
        if engine.dialect.name == "postgresql":
            for name in POSTGRES_PROTECTIONS:
                connection.exec_driver_sql(f"DROP FUNCTION {name}()")
    assert database_ready(engine)
    assert not database_ready(engine, require_loyalty=True)
    init_schema(engine)
    assert not (set(inspect(engine).get_table_names()) & LOYALTY_TABLES)
    upgrade_loyalty_configuration(engine)
    upgrade_loyalty_configuration(engine)
    assert database_ready(engine, require_loyalty=True)
    with factory() as session:
        assert [tuple(row) for row in session.execute(select(LoyaltyAccount.__table__))] == before
        assert [
            tuple(row) for row in session.execute(select(LoyaltyLedgerEntry.__table__))
        ] == ledger
        assert not session.scalars(select(LoyaltyStrategyVersion)).all()


def test_partial_schema_is_rejected(factory):
    with factory() as session:
        engine = session.get_bind()
    with engine.begin() as connection:
        LoyaltyConfigurationAudit.__table__.drop(connection)
    assert not database_ready(engine)
    with pytest.raises(RuntimeError):
        upgrade_loyalty_configuration(engine)
    with pytest.raises(RuntimeError):
        init_schema(engine)


def test_missing_immutability_trigger_is_rejected(factory):
    with factory() as session:
        engine = session.get_bind()
    name = LoyaltyStrategyVersion.__tablename__
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql(f"DROP TRIGGER {name}_update")
        else:
            connection.exec_driver_sql(f"DROP TRIGGER {name}_update ON {name}")
    assert not database_ready(engine, require_loyalty=True)
    with pytest.raises(RuntimeError):
        upgrade_loyalty_configuration(engine)


def test_http_permissions_scope_audit_and_disabled_flag(factory):
    with factory() as session:
        engine = session.get_bind()
    root = f"/api/operator/restaurants/{BID}/loyalty-config"
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as off:
        assert off.get(root + "/programs").status_code == 404
    with TestClient(
        create_app(
            engine=engine, payment_recovery_enabled=False, loyalty_configuration_enabled=True
        )
    ) as client:
        assert client.get(root + "/programs").status_code == 401
        viewer = staff_headers(client, role="viewer", name="loyalty.viewer")
        assert client.get(root + "/programs", headers=viewer).status_code == 200
        payload = {"request_key": "http", "document": document().model_dump(mode="json")}
        assert client.post(root + "/programs", json=payload, headers=viewer).status_code == 403
        manager = staff_headers(client, name="loyalty.manager")
        assert client.post(root + "/programs", json=payload).status_code == 403
        response = client.post(root + "/programs", json=payload, headers=manager)
        assert response.status_code == 200, response.text
        draft = response.json()
        reviewed = {"expected_revision": draft["revision"], "digest": draft["digest"]}
        saved = client.post(
            root + "/programs/" + draft["id"] + "/publish", json=reviewed, headers=manager
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["execution_enabled"] is False
        assert (
            client.get(
                "/api/operator/restaurants/other/loyalty-config/programs", headers=manager
            ).status_code
            == 403
        )
        assert (
            client.get(root + "/capabilities", headers=manager).json()["assignment_enabled"]
            is False
        )
    with factory() as session:
        assert len(session.scalars(select(LoyaltyConfigurationAudit)).all()) == 2


def test_concurrent_publication_is_idempotent(factory):
    with factory() as session:
        draft = create(LoyaltyConfigurationService(session, "manager"))

    def run(_):
        with factory() as session:
            service = LoyaltyConfigurationService(session, "manager")
            try:
                return publish(service, draft)["version_id"]
            except ConcurrencyConflictError:
                return publish(service, draft)["version_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(run, range(2)))
    assert ids[0] == ids[1]
    with factory() as session:
        assert len(session.scalars(select(LoyaltyStrategyVersion)).all()) == 1


def test_foreign_eligibility_rejected(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        for eligibility in ({"customer_ids": ["missing"]}, {"excluded_product_ids": ["missing"]}):
            with pytest.raises(ValidationError):
                create(service, eligibility=eligibility)


def test_feature_flag_requires_explicit_schema_and_valid_value(factory, monkeypatch):
    with factory() as session:
        engine = session.get_bind()
    monkeypatch.setenv("COMMERCE_LOYALTY_CONFIGURATION_ENABLED", "maybe")
    with pytest.raises(RuntimeError, match="must be 0 or 1"):
        create_app(engine=engine)
    monkeypatch.setenv("COMMERCE_LOYALTY_CONFIGURATION_ENABLED", "1")
    app = create_app(engine=engine, payment_recovery_enabled=False)
    assert any(r.path.endswith("/loyalty-config/capabilities") for r in app.routes)
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name in LOYALTY_TABLES:
                table.drop(connection)
    with pytest.raises(RuntimeError, match="explicit offline upgrade"):
        create_app(engine=engine, auto_init_schema=False)
    app = create_app(
        engine=engine, loyalty_configuration_enabled=False, payment_recovery_enabled=False
    )
    assert not any(r.path.endswith("/loyalty-config/capabilities") for r in app.routes)


def test_variant_set_cannot_be_extended_after_publication(factory):
    with factory() as session:
        service = LoyaltyConfigurationService(session, "manager")
        version = publish(service, create(service))
        draft = service.create(
            "experiments",
            BID,
            ExperimentCreate(request_key="exp", document=experiment(version["version_id"])),
        )
        saved = publish(service, draft, "experiments")
        session.add(
            LoyaltyExperimentVariant(
                experiment_version_id=saved["version_id"],
                business_id=BID,
                name="Extra control",
                allocation_bps=1,
            )
        )
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()
        assert len(session.scalars(select(LoyaltyExperimentVariant)).all()) == 2


def test_disabled_or_noop_history_guard_fails_readiness(factory):
    with factory() as session:
        engine = session.get_bind()
    name = LoyaltyStrategyVersion.__tablename__
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql(f"DROP TRIGGER {name}_update")
            connection.exec_driver_sql(
                f"CREATE TRIGGER {name}_update BEFORE UPDATE ON {name} BEGIN SELECT 1; END"
            )
        else:
            connection.exec_driver_sql(f"ALTER TABLE {name} DISABLE TRIGGER {name}_update")
    assert not database_ready(engine)
    with pytest.raises(RuntimeError):
        upgrade_loyalty_configuration(engine)


def test_postgresql_readiness_uses_bounded_bulk_reflection(factory):
    from sqlalchemy import event

    with factory() as session:
        engine = session.get_bind()
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        assert database_ready(engine, require_loyalty=False)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    if engine.dialect.name == "postgresql":
        assert len(statements) <= 20, len(statements)
