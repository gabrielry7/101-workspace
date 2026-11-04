"""Stage 4: independent cohorts, immutable assignment and actual checkout consumers."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, func, select, update
from sqlalchemy.exc import DBAPIError
from test_growth_v2 import pay_and_complete
from test_loyalty_configuration import create, document, experiment, publish
from test_loyalty_execution import balance, pg_only, refund
from test_payment_durability_m3 import factory as shared_factory
from test_payment_durability_m3 import request
from world_model.restaurant_commerce.db import database_ready
from world_model.restaurant_commerce.errors import IdempotencyConflictError, ValidationError
from world_model.restaurant_commerce.loyalty_assignment import (
    LoyaltyAssignmentService,
    assignment_bucket,
    assignment_summary,
    choose_variant,
)
from world_model.restaurant_commerce.loyalty_assignment_checkout import AssignmentCheckout
from world_model.restaurant_commerce.loyalty_assignment_migrations import upgrade_loyalty_assignment
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyAssignment as Assignment,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyAssignmentExposure as Exposure,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyAssignmentOrder as Binding,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyAssignmentOverlap as Overlap,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyEnrollmentDecision as Decision,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyExperimentRun as Run,
)
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_execution_migrations import upgrade_loyalty_execution
from world_model.restaurant_commerce.loyalty_execution_models import (
    LoyaltyOrderSnapshot as Snapshot,
)
from world_model.restaurant_commerce.loyalty_models import (
    LoyaltyExperiment,
    LoyaltyExperimentVersion,
    LoyaltyStrategy,
    LoyaltyStrategyVersion,
)
from world_model.restaurant_commerce.loyalty_schemas import (
    ExperimentCreate,
    ExperimentEdit,
    StrategyEdit,
)
from world_model.restaurant_commerce.models import Customer, LoyaltyAccount, Order, utcnow
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService

factory = shared_factory


def experiment_version(session, vid, **changes):
    config = LoyaltyConfigurationService(session, "synthetic-test")
    draft = config.create(
        "experiments",
        BID,
        ExperimentCreate(request_key=uuid4().hex, document=experiment(vid, **changes)),
    )
    return publish(config, draft, "experiments")["version_id"]


@pytest.fixture
def cohort(factory):
    upgrade_loyalty_execution(factory.kw["bind"])
    upgrade_loyalty_assignment(factory.kw["bind"])
    with factory() as session:
        config = LoyaltyConfigurationService(session, "synthetic-test")
        vid = publish(config, create(config, estimated_cost_per_point_minor=10))["version_id"]
        ev = experiment_version(session, vid, carryover_days=7)
        version = session.get(LoyaltyExperimentVersion, ev)
        # Select synthetic IDs in each deterministic arm. Production never chooses an arm.
        cids = {}
        while len(cids) < 2:
            cid = str(uuid4())
            arm = (
                "control"
                if assignment_bucket(version.random_salt, ev, BID, cid) < 5000
                else "points"
            )
            cids.setdefault(arm, cid)
        for arm, cid in cids.items():
            session.add(
                Customer(
                    id=cid,
                    business_id=BID,
                    name=arm,
                    phone="3005550600" if arm == "points" else "3005550601",
                )
            )
        session.commit()
        return factory, vid, ev, version.experiment_id, cids


def enroll(session, ev, cid, **kw):
    return LoyaltyAssignmentService(
        session, "synthetic-test", enabled=True, mode="synthetic"
    ).enroll(
        BID,
        ev,
        verified_customer_id=cid,
        identity_evidence_ref="synthetic-identity" if cid else None,
        request_key=kw.pop("request_key", uuid4().hex),
        **kw,
    )


def checkout(session, eid, cid, redeem=False):
    return RestaurantCommerceService(
        session,
        verified_customer_id=cid,
        loyalty_experiment=AssignmentCheckout(eid, redeem, True, "synthetic_tax_exclusive"),
    )


def req(svc, arm="points"):
    r = request(svc)
    if arm == "control":
        r.customer.phone = "3005550601"
    return r


def test_deterministic_allocation_boundaries():
    doc = experiment("x")
    assert choose_variant(doc, 0).name == "Control"
    assert choose_variant(doc, 4999).name == "Control"
    assert choose_variant(doc, 5000).name == "Points"
    assert choose_variant(doc, 9999).name == "Points"
    assert assignment_bucket("s", "e", "b", "c") == 9136


def test_enrollment_without_order_retries_restart_and_no_wallet(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        result = enroll(session, ev, cids["control"], request_key="stable")
        session.commit()
        assert result["eligible"] and result["assignment"]["control"]
        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(LoyaltyAccount)) == 0
    with factory() as session:
        assert enroll(session, ev, cids["control"], request_key="stable") == result
        assert enroll(session, ev, cids["control"]) == result
        session.commit()
        assert session.scalar(select(func.count()).select_from(Assignment)) == 1
        assert session.scalar(select(func.count()).select_from(Decision)) == 1
        assert session.scalar(select(func.count()).select_from(Exposure)) == 0
        summary = assignment_summary(session, BID, eid)
        assert summary["assigned_customers"] == 1 and summary["bound_orders"] == 0
        assert summary["profit_analysis_available"] is False
        with pytest.raises(IdempotencyConflictError):
            enroll(session, ev, cids["points"], request_key="stable")


def test_missing_foreign_identity_and_eligibility(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        denied = enroll(session, ev, None)
        assert denied["assignment"] is None
        assert denied["reasons"] == ["verified_identity_required"]
        session.commit()
        with pytest.raises(ValidationError, match="belong"):
            enroll(session, ev, str(uuid4()))
        session.rollback()
        restricted = experiment_version(session, vid, eligibility={"minimum_purchase_minor": 1})
        result = enroll(session, restricted, cids["points"])
        assert result["reasons"] == ["unsupported_pre_purchase_eligibility"]
        session.commit()
        assert session.scalar(select(func.count()).select_from(Assignment)) == 0


def test_versions_never_reassign_or_change_running_cohort(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        result = enroll(session, ev, cids["points"])
        session.commit()
        config = LoyaltyConfigurationService(session, "synthetic-test")
        current = config.get("experiments", BID, eid)
        edited = config.edit(
            "experiments",
            BID,
            eid,
            ExperimentEdit(
                expected_revision=current["revision"],
                document=experiment(vid, name="Edited proposal"),
            ),
        )
        newer = publish(config, edited, "experiments")["version_id"]
        assert enroll(session, newer, cids["points"]) == result
        session.commit()
        with pytest.raises(IdempotencyConflictError, match="frozen"):
            enroll(session, newer, cids["control"])
        session.rollback()
        session.get(LoyaltyExperiment, eid).state = "paused"
        session.commit()
        assert enroll(session, ev, cids["points"]) == result
        assert "experiment_not_enrolling" in enroll(session, ev, cids["control"])["reasons"]


@pytest.mark.parametrize(
    "first_allow,second_allow,accepted",
    [(False, False, False), (False, True, False), (True, False, False), (True, True, True)],
)
def test_overlap_requires_both_policies_including_control(
    cohort, first_allow, second_allow, accepted
):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        first = experiment_version(
            session,
            vid,
            allow_overlap=first_allow,
            overlap_reason="Synthetic overlap protocol" if first_allow else None,
        )
        second = experiment_version(
            session,
            vid,
            allow_overlap=second_allow,
            overlap_reason="Synthetic overlap protocol" if second_allow else None,
        )
        assert enroll(session, first, cids["control"])["eligible"]
        second_result = enroll(session, second, cids["control"])
        assert second_result["eligible"] == accepted
        if not accepted:
            assert second_result["reasons"] == ["overlap_protected"]
        session.commit()
        assert session.scalar(select(func.count()).select_from(Overlap)) == int(accepted)
        if accepted:
            other_id = session.get(LoyaltyExperimentVersion, second).experiment_id
            assert assignment_summary(session, BID, other_id)["warnings"] == [
                "experiment_contamination"
            ]


def test_exposure_is_explicit_idempotent_scoped_and_distinct(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        assigned = enroll(session, ev, cids["points"])["assignment"]
        session.commit()
        svc = checkout(session, eid, cids["points"])
        order = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        assert session.scalar(select(func.count()).select_from(Exposure)) == 0
        assert balance(session, cids["points"]).available_points > 0
        api = LoyaltyAssignmentService(session, "renderer", enabled=True, mode="synthetic")
        args = dict(
            verified_customer_id=cids["points"],
            kind="offer_surface_rendered",
            surface="synthetic-view",
            source_ref="receipt-1",
        )
        exposure = api.record_exposure(BID, assigned["assignment_id"], request_key="first", **args)
        session.commit()
        assert (
            api.record_exposure(BID, assigned["assignment_id"], request_key="second", **args)
            == exposure
        )
        session.commit()
        assert assignment_summary(session, BID, eid)["bound_orders"] == 1
        assert session.get(Binding, order.id).assignment_id == assigned["assignment_id"]
        with pytest.raises(ValidationError, match="kind"):
            api.record_exposure(
                BID,
                assigned["assignment_id"],
                request_key="bad",
                **{**args, "kind": "control_surface_rendered"},
            )
        session.rollback()
        with pytest.raises(ValidationError, match="identity"):
            api.record_exposure(
                BID,
                assigned["assignment_id"],
                request_key="foreign",
                **{**args, "verified_customer_id": cids["control"]},
            )


@pytest.mark.parametrize("arm", ["control", "points"])
def test_checkout_consumes_assignment_baseline_completion_and_refund(cohort, arm):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        assigned = enroll(session, ev, cids[arm])["assignment"]
        session.commit()
        svc = checkout(session, eid, cids[arm])
        r = req(svc, arm)
        order = pay_and_complete(svc, svc.create_order(BID, r))
        binding = session.get(Binding, order.id)
        assert binding.assignment_id == assigned["assignment_id"]
        snapshot = session.get(Snapshot, order.id)
        assert (snapshot is None) == (arm == "control")
        expected = order.total_minor // 1000 * (2 if arm == "points" else 1)
        assert balance(session, cids[arm]).available_points == expected
        session.get(LoyaltyExperiment, eid).state = "paused"
        session.commit()
        assert svc.create_order(BID, r).id == order.id
        refund(svc, order, order.total_minor)
        assert balance(session, cids[arm]).available_points == 0


def test_retry_before_enrollment_and_pause_preserves_binding(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        svc = checkout(session, eid, cids["points"])
        r = req(svc)
        order = svc.create_order(BID, r)
        assert session.get(Binding, order.id).reason == "not_enrolled"
        enroll(session, ev, cids["points"])
        session.commit()
        assert svc.create_order(BID, r).id == order.id
        assert session.get(Snapshot, order.id) is None
        session.get(LoyaltyExperiment, eid).state = "paused"
        session.commit()
        new = svc.create_order(BID, req(svc))
        assert session.get(Binding, new.id).reason == "experiment_paused_or_archived"
        assert session.get(Snapshot, new.id) is None


def test_program_edit_preserves_assigned_rules_and_pause_falls_back(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        enroll(session, ev, cids["points"])
        session.commit()
        config = LoyaltyConfigurationService(session, "test")
        pid = session.get(LoyaltyStrategyVersion, vid).strategy_id
        current = config.get("programs", BID, pid)
        config.edit(
            "programs",
            BID,
            pid,
            StrategyEdit(
                expected_revision=current["revision"],
                document=document(
                    name="Different future rate",
                    earning={"type": "points", "spend_minor_per_point": 500},
                ),
            ),
        )
        svc = checkout(session, eid, cids["points"])
        order = svc.create_order(BID, req(svc))
        assert session.get(Snapshot, order.id).version_id == vid
        session.get(LoyaltyStrategy, pid).state = "paused"
        session.commit()
        new = svc.create_order(BID, req(svc))
        assert session.get(Binding, new.id).reason == "program_paused_or_archived"


def test_guest_checkout_does_not_enroll_contact_identity(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        svc = checkout(session, eid, None)
        order = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        assert session.get(Binding, order.id).reason == "unverified_identity"
        assert session.get(Snapshot, order.id) is None
        assert session.scalar(select(func.count()).select_from(Assignment)) == 0
        assert not json.loads(session.get(Order, order.id).customer_snapshot_json)[
            "identity_verified"
        ]


def test_assignment_migration_immutable_and_readiness(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        enroll(session, ev, cids["points"])
        session.commit()
    upgrade_loyalty_assignment(factory.kw["bind"])
    assert database_ready(factory.kw["bind"], require_loyalty=True)
    with factory() as session:
        for model in (Assignment, Decision, Run):
            for statement in (
                delete(model),
                update(model).values(
                    **(
                        {"algorithm": "sha256-v1"}
                        if model is Assignment
                        else {"actor_id": "tamper"}
                    )
                ),
            ):
                with pytest.raises(DBAPIError):
                    session.execute(statement)
                    session.commit()
                session.rollback()
        assert session.scalar(select(func.count()).select_from(Assignment)) == 1


def test_postgres_concurrent_enrollment_and_overlap(cohort):
    factory, vid, ev, eid, cids = cohort
    pg_only(factory)

    def worker(version):
        with factory() as session:
            result = enroll(session, version, cids["points"])
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, [ev] * 4))
    assert len({r["assignment"]["assignment_id"] for r in results}) == 1
    with factory() as session:
        others = [experiment_version(session, vid) for _ in range(2)]
        session.commit()

    def other(version):
        with factory() as session:
            result = enroll(session, version, cids["control"])
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(other, others))
    assert sum(r["eligible"] for r in results) == 1


def test_postgres_readiness_query_bound(cohort):
    factory, *_ = cohort
    pg_only(factory)
    engine = factory.kw["bind"]
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        assert database_ready(engine, require_loyalty=True)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(queries) <= 20


def test_carryover_protects_then_releases_without_reassignment(cohort, monkeypatch):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        first = enroll(session, ev, cids["control"])
        session.commit()
        assignment = session.get(Assignment, first["assignment"]["assignment_id"])
        from world_model.restaurant_commerce.loyalty_wallet import aware

        other = experiment_version(session, vid, enrollment_end=utcnow() + timedelta(days=365))
        session.commit()
        future = aware(assignment.evaluation_ends_at) + timedelta(seconds=1)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_assignment.utcnow", lambda: future
        )
        assert enroll(session, other, cids["control"])["reasons"] == ["overlap_protected"]
        session.commit()
        future = aware(assignment.exclusion_ends_at) + timedelta(seconds=1)
        assert enroll(session, other, cids["control"])["eligible"]
        assert enroll(session, ev, cids["control"]) == first


@pytest.mark.parametrize(
    "reason,changes",
    [
        ("offer_ineligible", {"eligibility": {"minimum_purchase_minor": 99999999}}),
        ("budget_exhausted", {"per_customer_budget_minor": 1}),
    ],
)
def test_ineligible_or_exhausted_offer_preserves_checkout(cohort, reason, changes):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        config = LoyaltyConfigurationService(session, "test")
        vid = publish(
            config, create(config, key=uuid4().hex, estimated_cost_per_point_minor=10, **changes)
        )["version_id"]
        ev = treatment_experiment(session, vid, cids["points"])
        result = enroll(session, ev, cids["points"])
        assert not result["assignment"]["control"]
        eid = result["assignment"]["experiment_id"]
        session.commit()
        svc = checkout(session, eid, cids["points"])
        order = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        assert session.get(Binding, order.id).reason == reason
        assert session.get(Snapshot, order.id) is None
        assert balance(session, cids["points"]).available_points == order.total_minor // 1000


def test_http_diagnostics_scoped_flagged_and_no_enrollment_endpoint(cohort):
    from fastapi.testclient import TestClient
    from staff_helpers import staff_headers
    from world_model.restaurant_commerce.api import create_app

    factory, vid, ev, eid, cids = cohort
    engine = factory.kw["bind"]
    root = f"/api/operator/restaurants/{BID}/loyalty-config"
    with factory() as session:
        enroll(session, ev, cids["control"])
        session.commit()
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as client:
        assert client.get(root + f"/experiments/{eid}/enrollment").status_code == 404
    with TestClient(
        create_app(
            engine=engine, payment_recovery_enabled=False, loyalty_configuration_enabled=True
        )
    ) as client:
        path = root + f"/experiments/{eid}/enrollment"
        assert client.get(path).status_code == 401
        viewer = staff_headers(client, role="viewer", name="assignment-viewer")
        response = client.get(path, headers=viewer)
        assert response.status_code == 200, response.text
        assert response.json()["assigned_customers"] == 1
        assert client.get(path.replace(BID, "other"), headers=viewer).status_code == 403
        assert (
            client.post(
                path, json={"verified_customer_id": cids["points"]}, headers=viewer
            ).status_code
            == 405
        )
        assert (
            client.get(root + "/capabilities", headers=viewer).json()["assignment_enabled"] is False
        )


def test_missing_guard_fails_readiness_and_offline_upgrade(cohort):
    factory, *_ = cohort
    engine = factory.kw["bind"]
    with engine.begin() as conn:
        statement = "DROP TRIGGER restaurant_loyalty_assignments_insert_scope"
        if engine.dialect.name == "postgresql":
            statement += " ON restaurant_loyalty_assignments"
        conn.exec_driver_sql(statement)
    assert not database_ready(engine, require_loyalty=True)
    with pytest.raises(RuntimeError, match="partial schema"):
        upgrade_loyalty_assignment(engine)


def treatment_experiment(session, vid, cid):
    # Select synthetic test configuration only; actual enroll() is never overridden.
    while True:
        ev = experiment_version(session, vid)
        version = session.get(LoyaltyExperimentVersion, ev)
        if assignment_bucket(version.random_salt, ev, BID, cid) >= 5000:
            return ev


def test_fixed_redemption_usage_and_existing_reward_priority(cohort):
    from test_loyalty_execution import fixed_version
    from world_model.restaurant_commerce.models import RewardDefinition, RewardRedemption

    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        vid = fixed_version(session)
        ev = treatment_experiment(session, vid, cids["points"])
        result = enroll(session, ev, cids["points"])
        eid = result["assignment"]["experiment_id"]
        session.commit()
        svc = checkout(session, eid, cids["points"], redeem=True)
        first = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        assert session.get(Binding, first.id).reason == "incremental_earning_only"
        second = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        assert second.reward_discount_minor == 1000
        assert session.get(Snapshot, second.id).version_id == vid
        assert session.scalar(select(func.count()).select_from(RewardRedemption)) == 1
        assert session.scalar(select(func.count()).select_from(Exposure)) == 0
        legacy = RewardDefinition(
            business_id=BID, name="Existing benefit", points_cost=1, discount_minor=500
        )
        session.add(legacy)
        session.commit()
        r = req(svc).model_copy(update={"reward_id": legacy.id})
        third = pay_and_complete(svc, svc.create_order(BID, r))
        assert third.reward_discount_minor == 500
        assert session.get(Binding, third.id).reason == "baseline_reward_priority"
        assert session.get(Snapshot, third.id) is None


def test_quote_cannot_mark_a_reservation_snapshot(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        enroll(session, ev, cids["points"])
        session.commit()
        svc = checkout(session, eid, cids["points"])
        r = req(svc)
        svc.quote(BID, r.items, customer_phone=r.customer.phone)
        assert svc._assignment_choice.selection is not None
        assert "loyalty_execution_version" not in json.loads(svc._snapshot(BID, r))


def test_wrong_experiment_run_is_rejected_by_database(cohort):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        other = experiment_version(session, vid)
        session.commit()
        session.add(
            Run(
                experiment_id=eid,
                business_id=BID,
                experiment_version_id=other,
                actor_id="tamper",
                opened_at=utcnow(),
            )
        )
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()
        assert session.get(Run, eid) is None


def test_postgres_enrollment_rechecks_time_after_lock_wait(cohort, monkeypatch):
    from threading import Event

    factory, vid, ev, eid, cids = cohort
    pg_only(factory)
    reached = Event()
    clock = [utcnow()]
    monkeypatch.setattr(
        "world_model.restaurant_commerce.loyalty_assignment.utcnow", lambda: clock[0]
    )

    def worker():
        with factory() as session:

            def capture(conn, cursor, statement, parameters, context, executemany):
                if "restaurant_customers" in statement and "FOR UPDATE" in statement:
                    reached.set()

            event.listen(session.connection(), "before_cursor_execute", capture)
            result = enroll(session, ev, cids["points"])
            session.commit()
            return result

    with factory() as blocker:
        blocker.scalar(select(Customer).where(Customer.id == cids["points"]).with_for_update())
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker)
            assert reached.wait(10)
            clock[0] += timedelta(days=31)
            blocker.commit()
            result = future.result(timeout=30)
    assert result["reasons"] == ["outside_enrollment_window"]
    assert result["assignment"] is None


def test_assignment_schema_stays_explicit(factory):
    from sqlalchemy import inspect
    from world_model.restaurant_commerce.db import init_schema
    from world_model.restaurant_commerce.loyalty_assignment_models import ASSIGNMENT_TABLES

    engine = factory.kw["bind"]
    init_schema(engine)
    assert not set(inspect(engine).get_table_names()) & ASSIGNMENT_TABLES
    with pytest.raises(RuntimeError, match="execution upgrade"):
        upgrade_loyalty_assignment(engine)
    assert not set(inspect(engine).get_table_names()) & ASSIGNMENT_TABLES


def test_expiry_at_final_reservation_is_atomic(cohort, monkeypatch):
    from world_model.restaurant_commerce import loyalty_execution

    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        result = enroll(session, ev, cids["points"])
        session.commit()
        original = loyalty_execution.budgets
        future = utcnow() + timedelta(days=366)

        def after_locks(*args, **kw):
            rows = original(*args, **kw)
            monkeypatch.setattr(
                "world_model.restaurant_commerce.loyalty_assignment_checkout.utcnow", lambda: future
            )
            return rows

        monkeypatch.setattr(loyalty_execution, "budgets", after_locks)
        svc = checkout(session, eid, cids["points"])
        with pytest.raises(ValidationError, match="window ended"):
            svc.create_order(BID, req(svc))
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Order)) == 0
        assert session.scalar(select(func.count()).select_from(Snapshot)) == 0
        assert enroll(session, ev, cids["points"]) == result


def test_late_exposure_and_sql_history_retention(cohort, monkeypatch):
    factory, vid, ev, eid, cids = cohort
    with factory() as session:
        assigned = enroll(session, ev, cids["points"])["assignment"]
        session.commit()
        svc = checkout(session, eid, cids["points"])
        order = pay_and_complete(svc, svc.create_order(BID, req(svc)))
        summary = assignment_summary(session, BID, eid)
        assert any(
            row["reason"] == "loyalty.earned" and row["net_points"] > 0
            for row in summary["reward_ledger_activity"]
        )
        session.get(LoyaltyExperiment, eid).state = "paused"
        session.commit()
        future = utcnow() + timedelta(days=366)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_assignment.utcnow", lambda: future
        )
        api = LoyaltyAssignmentService(session, "renderer", enabled=True, mode="synthetic")
        result = api.record_exposure(
            BID,
            assigned["assignment_id"],
            verified_customer_id=cids["points"],
            request_key="late",
            kind="offer_surface_rendered",
            surface="synthetic",
            source_ref="late-receipt",
        )
        session.commit()
        assert result["warnings"] == ["outside_offer_window", "experiment_paused_or_archived"]
        for statement in (
            delete(Exposure),
            update(Exposure).values(surface="tamper"),
            delete(Binding),
            update(Binding).values(reason="control"),
        ):
            with pytest.raises(DBAPIError):
                session.execute(statement)
                session.commit()
            session.rollback()
        assert session.get(Binding, order.id).assignment_id == assigned["assignment_id"]


def test_postgres_concurrent_assignment_redemption_does_not_double_spend(cohort):
    from test_loyalty_execution import fixed_version

    factory, vid, ev, eid, cids = cohort
    pg_only(factory)
    with factory() as session:
        baseline = RestaurantCommerceService(session, verified_customer_id=cids["points"])
        pay_and_complete(baseline, baseline.create_order(BID, req(baseline)))
        available = balance(session, cids["points"]).available_points
        vid = fixed_version(session, points=available)
        ev = treatment_experiment(session, vid, cids["points"])
        result = enroll(session, ev, cids["points"])
        eid = result["assignment"]["experiment_id"]
        session.commit()

    def worker(_):
        with factory() as session:
            svc = checkout(session, eid, cids["points"], redeem=True)
            return svc.create_order(BID, req(svc)).reward_discount_minor

    with ThreadPoolExecutor(max_workers=2) as pool:
        discounts = list(pool.map(worker, range(2)))
    assert sorted(discounts) == [0, 1000]
    with factory() as session:
        assert balance(session, cids["points"]).available_points == 0
        assert session.scalar(select(func.count()).select_from(Assignment)) == 1
