"""Known-outcome ITT cohorts, financial coverage, historical rules and uncertainty."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fractions import Fraction
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as SchemaError
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.exc import DBAPIError
from staff_helpers import staff_headers
from test_growth_v2 import pay_and_complete
from test_loyalty_assignment import enroll, experiment_version
from test_loyalty_configuration import create, publish
from test_loyalty_execution import refund
from test_payment_durability_m3 import factory as factory  # noqa: PLC0414
from test_payment_durability_m3 import request
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.db import database_ready
from world_model.restaurant_commerce.errors import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
)
from world_model.restaurant_commerce.loyalty_analytics import report
from world_model.restaurant_commerce.loyalty_analytics_routes import csv_report
from world_model.restaurant_commerce.loyalty_assignment import assignment_bucket
from world_model.restaurant_commerce.loyalty_assignment_migrations import (
    upgrade_loyalty_assignment,
)
from world_model.restaurant_commerce.loyalty_assignment_models import (
    LoyaltyAssignment,
    LoyaltyAssignmentExposure,
)
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_execution_migrations import (
    upgrade_loyalty_execution,
)
from world_model.restaurant_commerce.loyalty_measurement_evidence import (
    OperatingCost,
    OrderCosts,
    context,
    record,
)
from world_model.restaurant_commerce.loyalty_measurement_migrations import (
    TABLE,
    upgrade_loyalty_measurement,
)
from world_model.restaurant_commerce.loyalty_measurement_models import (
    LoyaltyFinancialEvidence,
)
from world_model.restaurant_commerce.loyalty_models import LoyaltyExperimentVersion
from world_model.restaurant_commerce.loyalty_schemas import (
    ExperimentDocument,
    ExperimentEdit,
)
from world_model.restaurant_commerce.loyalty_statistics import decimal, welch_interval
from world_model.restaurant_commerce.models import (
    Customer,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    Order,
    Payment,
    PaymentReconciliation,
    utcnow,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID
from world_model.restaurant_commerce.service import RestaurantCommerceService


@pytest.fixture
def analytics(factory, monkeypatch):
    engine = factory.kw["bind"]
    upgrade_loyalty_execution(engine)
    upgrade_loyalty_assignment(engine)
    upgrade_loyalty_measurement(engine)
    clock = utcnow()
    monkeypatch.setattr(
        "world_model.restaurant_commerce.loyalty_analytics.utcnow",
        lambda: clock + timedelta(days=92),
    )

    def build(n=4, protocol=True, group="loyalty"):
        with factory() as s:
            cfg = LoyaltyConfigurationService(s, "synthetic")
            vid = publish(cfg, create(cfg, key=uuid4().hex, estimated_cost_per_point_minor=10))[
                "version_id"
            ]
            ev = experiment_version(
                s,
                vid,
                enrollment_start=clock - timedelta(minutes=1),
                enrollment_end=clock + timedelta(days=1),
                observation_days=30,
                exclusion_group=group,
                analysis_protocol={
                    "sample_size_rationale": "Synthetic design validates customer-level comparisons.",
                    "minimum_customers_per_arm": 30,
                    "readout_at": clock + timedelta(days=31),
                }
                if protocol
                else None,
            )
            version = s.get(LoyaltyExperimentVersion, ev)
            ids, rows = {"control": [], "treatment": []}, []
            while min(map(len, ids.values())) < n:
                cid = str(uuid4())
                arm = (
                    "control"
                    if assignment_bucket(version.random_salt, ev, BID, cid) < 5000
                    else "treatment"
                )
                if len(ids[arm]) >= n:
                    continue
                phone = str(3006000000 + len(rows))
                s.add(Customer(id=cid, business_id=BID, name=arm, phone=phone))
                s.commit()
                assignment = enroll(s, ev, cid)
                s.commit()
                assert assignment["eligible"], assignment
                a = s.get(LoyaltyAssignment, assignment["assignment"]["assignment_id"])
                i = len(ids[arm])
                oid = None
                profit = 0
                if i % 2 == 0:
                    svc = RestaurantCommerceService(s, verified_customer_id=cid)
                    req = request(svc)
                    req.customer.phone = phone
                    order = pay_and_complete(svc, svc.create_order(BID, req))
                    oid = order.id
                    profit = (3000 if arm == "control" else 6000) + i * 10
                    write_cost(s, oid, variable=order.total_minor - profit - 200, reward=200)
                ids[arm].append(cid)
                rows.append(
                    {
                        "customer_id": cid,
                        "assignment_id": a.id,
                        "variant_id": a.variant_id,
                        "order_id": oid,
                        "profit": profit,
                        "arm": arm,
                    }
                )
            for variant_id in {r["variant_id"] for r in rows}:
                write_operating(s, variant_id, 400)
            return {
                "factory": factory,
                "version_id": ev,
                "experiment_id": version.experiment_id,
                "rows": rows,
                "clock": clock,
                "program_version": vid,
            }

    return build


def write_cost(s, oid, variable=10000, reward=0, key=None, **changes):
    current = context(s, BID, "orders", oid)
    payload = OrderCosts(
        request_key=key or uuid4().hex,
        expected_revision=current["latest"]["revision"],
        financial_digest=current["financial_digest"],
        source_ref="synthetic-finance-source",
        includes_estimate=False,
        variable_cost_minor=variable,
        additional_reward_cost_minor=reward,
        **changes,
    )
    return record(s, BID, "orders", oid, payload, "synthetic-finance")


def write_operating(s, variant_id, amount):
    current = context(s, BID, "variants", variant_id)
    return record(
        s,
        BID,
        "variants",
        variant_id,
        OperatingCost(
            request_key=uuid4().hex,
            expected_revision=current["latest"]["revision"],
            financial_digest=current["financial_digest"],
            source_ref="synthetic-full-experiment-cost",
            includes_estimate=False,
            operating_cost_minor=amount,
        ),
        "synthetic-finance",
    )


def test_known_effect_includes_nonbuyers_and_unbound_verified_orders(analytics):
    data = analytics()
    with data["factory"]() as s:
        before = s.scalar(select(func.count()).select_from(LoyaltyLedgerEntry))
        result = report(s, BID, data["experiment_id"])
        for arm in result["arms"]:
            members = [r for r in data["rows"] if r["variant_id"] == arm["variant_id"]]
            expected = Fraction(sum(r["profit"] for r in members) - 400, 4)
            assert arm["assigned_customers"] == 4
            assert arm["nonbuyers"] == 2
            assert arm["profit_per_assigned_minor"] == decimal(expected)
            assert arm["purchase_frequency"] == "0.500000"
            assert arm["exposed_customers"] == 0
            assert arm["repeat_purchase"]["30"]["eligible_assigned"] == 4
        assert result["comparisons"][0]["incremental_profit_per_assigned_minor"] == "1500.000000"
        assert result["comparisons"][0]["confidence_interval"] is None
        assert result["automatic_winner"] is None
        assert s.scalar(select(func.count()).select_from(LoyaltyLedgerEntry)) == before
        assert report(s, BID, data["experiment_id"])["data_revision"] == result["data_revision"]


def test_report_interval_uses_original_customer_units_and_planned_window(analytics):
    data = analytics(n=30)
    with data["factory"]() as s:
        result = report(s, BID, data["experiment_id"])
        assert result["primary_evaluation_complete"]
        comparison = result["comparisons"][0]
        expected = welch_interval(
            [r["profit"] for r in data["rows"] if r["arm"] == "treatment"],
            [r["profit"] for r in data["rows"] if r["arm"] == "control"],
        )
        assert comparison["confidence_interval"] == expected
        assert result["assigned_customers"] == 60
        assert sum(a["nonbuyers"] for a in result["arms"]) == 30


def test_missing_costs_remain_missing_and_refund_invalidates_then_corrects(analytics):
    data = analytics()
    target = next(r for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        old = report(s, BID, data["experiment_id"])
        svc = RestaurantCommerceService(s)
        order = svc.order_out(target["order_id"])
        refund(svc, order, 1000, reference="analytics-partial")
        result = report(s, BID, data["experiment_id"])
        arm = next(a for a in result["arms"] if a["variant_id"] == target["variant_id"])
        assert arm["profit_per_assigned_minor"] is None
        assert arm["assigned_customers"] == 4
        assert result["data_revision"] != old["data_revision"]
        assert result["missing_orders"]["total"] == 1
        assert result["missing_orders"]["items"][0]["stale"]
        previous = context(s, BID, "orders", order.id)["latest"]["document"]
        write_cost(
            s,
            order.id,
            variable=previous["variable_cost_minor"],
            reward=previous["additional_reward_cost_minor"],
        )
        fixed = report(s, BID, data["experiment_id"])
        fixed_arm = next(a for a in fixed["arms"] if a["variant_id"] == target["variant_id"])
        assert (
            Fraction(fixed_arm["profit_per_assigned_minor"])
            == Fraction(
                next(a for a in old["arms"] if a["variant_id"] == target["variant_id"])[
                    "profit_per_assigned_minor"
                ]
            )
            - 250
        )
        assert s.scalar(select(func.count()).select_from(LoyaltyFinancialEvidence)) == 7


def test_orderless_credit_changes_revision_and_never_becomes_free_profit(analytics):
    data = analytics()
    target = next(r for r in data["rows"] if not r["order_id"])
    with data["factory"]() as s:
        first = report(s, BID, data["experiment_id"])
        account = LoyaltyAccount(
            business_id=BID, customer_id=target["customer_id"], available_points=10
        )
        s.add(account)
        s.flush()
        s.add(
            LoyaltyLedgerEntry(
                account_id=account.id,
                delta_points=10,
                reason="manual.credit",
                idempotency_key=uuid4().hex,
            )
        )
        s.commit()
        after = report(s, BID, data["experiment_id"])
        assert after["data_revision"] != first["data_revision"]
        assert "unattributed_reward_cost" in after["warnings"]
        assert (
            next(a for a in after["arms"] if a["variant_id"] == target["variant_id"])[
                "profit_per_assigned_minor"
            ]
            is None
        )


def test_immature_and_legacy_protocol_are_descriptive(analytics, monkeypatch):
    data = analytics(protocol=False)
    monkeypatch.setattr(
        "world_model.restaurant_commerce.loyalty_analytics.utcnow",
        lambda: utcnow() + timedelta(days=10),
    )
    with data["factory"]() as s:
        result = report(s, BID, data["experiment_id"])
        assert result["mature_customers"] == 0
        assert "incomplete_observation_windows" in result["warnings"]
        assert "analysis_protocol_missing" in result["warnings"]
        assert all(a["repeat_purchase"]["30"]["eligible_assigned"] == 0 for a in result["arms"])
        assert result["comparisons"][0]["confidence_interval"] is None


def test_unverified_contact_match_does_not_enter_variant_revenue(analytics):
    data = analytics()
    target = data["rows"][0]
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        svc = RestaurantCommerceService(s)
        req = request(svc)
        req.customer.phone = s.get(Customer, target["customer_id"]).phone
        pay_and_complete(svc, svc.create_order(BID, req))
        after = report(s, BID, data["experiment_id"])
        assert [a["net_revenue_minor"] for a in before["arms"]] == [
            a["net_revenue_minor"] for a in after["arms"]
        ]
        assert after["coverage"]["unverified_financial_orders"] == 1
        assert "identity_coverage_incomplete" in after["warnings"]
        assert "identity_unverified_outcome" in after["warnings"]
        assert (
            next(a for a in after["arms"] if a["variant_id"] == target["variant_id"])[
                "profit_per_assigned_minor"
            ]
            is None
        )


def test_financial_review_is_order_scoped_and_preserves_unavailability(analytics):
    data = analytics()
    oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        s.add(
            PaymentReconciliation(
                order_id=oid,
                business_id=BID,
                reason="manual_review",
                status="open",
                evidence_json="{}",
            )
        )
        s.commit()
        result = report(s, BID, data["experiment_id"])
        assert "financial_review_open" in result["warnings"]


def test_pending_checkout_with_open_financial_review_is_not_zero_profit(analytics):
    data = analytics()
    target = next(r for r in data["rows"] if not r["order_id"])
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        assert (
            next(a for a in before["arms"] if a["variant_id"] == target["variant_id"])[
                "profit_per_assigned_minor"
            ]
            is not None
        )
        svc = RestaurantCommerceService(s, verified_customer_id=target["customer_id"])
        req = request(svc)
        req.customer.phone = s.get(Customer, target["customer_id"]).phone
        pending = svc.create_order(BID, req)
        assert pending.payment_status != "paid"
        s.add(
            PaymentReconciliation(
                order_id=pending.id,
                business_id=BID,
                reason="provider_timeout",
                status="open",
                evidence_json="{}",
            )
        )
        s.commit()
        result = report(s, BID, data["experiment_id"])
        arm = next(a for a in result["arms"] if a["variant_id"] == target["variant_id"])
        assert arm["assigned_customers"] == 4
        assert arm["profit_per_assigned_minor"] is None
        assert "financial_review_open" in result["warnings"]
        assert "unresolved_order_at_window" in result["warnings"]


def test_evidence_retry_conflict_and_immutable_history(analytics):
    data = analytics()
    oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        ctx = context(s, BID, "orders", oid)
        payload = OrderCosts(
            request_key="replayed-cost",
            expected_revision=ctx["latest"]["revision"],
            financial_digest=ctx["financial_digest"],
            source_ref="synthetic-source",
            includes_estimate=False,
            variable_cost_minor=100,
            additional_reward_cost_minor=200,
        )
        result = record(s, BID, "orders", oid, payload, "test")
        assert record(s, BID, "orders", oid, payload, "test") == result
        with pytest.raises(IdempotencyConflictError):
            record(
                s,
                BID,
                "orders",
                oid,
                payload.model_copy(update={"variable_cost_minor": 101}),
                "test",
            )
        with pytest.raises(ConcurrencyConflictError):
            record(
                s,
                BID,
                "orders",
                oid,
                payload.model_copy(update={"request_key": "stale"}),
                "test",
            )
        with pytest.raises(DBAPIError):
            s.execute(
                text(f"UPDATE {TABLE} SET source_ref='changed' WHERE id=:id"),
                {"id": result["id"]},
            )
            s.commit()
        s.rollback()
        with pytest.raises(DBAPIError):
            s.execute(text(f"DELETE FROM {TABLE} WHERE id=:id"), {"id": result["id"]})
        s.rollback()


def test_concurrent_cost_corrections_have_one_winner(analytics):
    data = analytics()
    oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        ctx = context(s, BID, "orders", oid)

    def worker(i):
        with data["factory"]() as s:
            try:
                record(
                    s,
                    BID,
                    "orders",
                    oid,
                    OrderCosts(
                        request_key=f"race-{i}",
                        expected_revision=ctx["latest"]["revision"],
                        financial_digest=ctx["financial_digest"],
                        source_ref="synthetic-race",
                        includes_estimate=False,
                        variable_cost_minor=i,
                        additional_reward_cost_minor=0,
                    ),
                    "test",
                )
                return "won"
            except ConcurrencyConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker, [10, 20])) == ["conflict", "won"]


def test_welch_known_result_large_offset_and_multiple_comparisons():
    x, y = [10, 12, 14], [0, 2, 4]
    expected = welch_interval(x, y)
    assert (expected["lower_minor"], expected["upper_minor"]) == ("5", "15")
    offset = 10**22
    assert welch_interval([v + offset for v in x], [v + offset for v in y]) == expected
    wider = welch_interval(x, y, comparisons=3)
    assert int(wider["lower_minor"]) < 5 and int(wider["upper_minor"]) > 15
    assert welch_interval([0] * 40, [0] * 40) is None
    from math import ceil, floor

    from scipy.stats import ttest_ind

    unequal_x, unequal_y = [0, 0, 2, 3, 5], [1, 10, 40]
    reference = ttest_ind(unequal_x, unequal_y, equal_var=False).confidence_interval(
        confidence_level=1 - 0.05 / 3
    )
    actual = welch_interval(unequal_x, unequal_y, comparisons=3)
    assert int(actual["lower_minor"]) == floor(reference.low)
    assert int(actual["upper_minor"]) == ceil(reference.high)


def test_upgrade_repeatability_and_missing_guards(analytics):
    data = analytics()
    engine = data["factory"].kw["bind"]
    upgrade_loyalty_measurement(engine)
    assert database_ready(engine, require_measurement=True)
    with engine.begin() as c:
        c.exec_driver_sql(
            f"DROP TRIGGER {TABLE}_update"
            + (f" ON {TABLE}" if engine.dialect.name == "postgresql" else "")
        )
    assert not database_ready(engine, require_measurement=True)
    with pytest.raises(RuntimeError, match="Partial measurement"):
        upgrade_loyalty_measurement(engine)


def test_api_roles_flags_tenant_scope_csv_and_no_wallet_writes(analytics):
    data = analytics()
    app = create_app(
        engine=data["factory"].kw["bind"],
        loyalty_configuration_enabled=True,
        loyalty_analytics_enabled=True,
        payment_recovery_enabled=False,
    )
    root = f"/api/operator/restaurants/{BID}/loyalty-config"
    with TestClient(app) as client:
        headers = staff_headers(client, role="viewer", name="analytics.viewer")
        path = root + f"/experiments/{data['experiment_id']}/report"
        assert client.get(path).status_code == 200
        assert client.get(path + ".csv").status_code == 200
        oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
        ctx = client.get(root + "/analytics/orders/" + oid).json()
        body = {
            "request_key": "role-cost",
            "expected_revision": ctx["latest"]["revision"],
            "financial_digest": ctx["financial_digest"],
            "source_ref": "source-test",
            "includes_estimate": False,
            "variable_cost_minor": 1000,
            "additional_reward_cost_minor": 0,
        }
        assert (
            client.post(root + "/analytics/orders/" + oid, json=body, headers=headers).status_code
            == 403
        )
        headers = staff_headers(client, role="finance", name="analytics.finance")
        assert client.post(root + "/analytics/orders/" + oid, json=body).status_code == 403
        assert (
            client.post(root + "/analytics/orders/" + oid, json=body, headers=headers).status_code
            == 200
        )
        assert client.get(path.replace(BID, "other-business")).status_code == 403
        assert client.get(root + "/analytics/orders/missing").status_code == 404
    disabled = create_app(
        engine=data["factory"].kw["bind"],
        loyalty_configuration_enabled=True,
        payment_recovery_enabled=False,
    )
    with TestClient(disabled) as client:
        staff_headers(client)
        assert client.get(path).status_code == 404
        assert client.get(root + "/capabilities").json()["execution_enabled"] is False


def test_protocol_overflow_and_non_scalar_unicode_are_validation_errors():
    from test_loyalty_configuration import experiment

    doc = experiment("version").model_dump()
    doc.update(
        enrollment_end="9999-12-31T00:00:00Z",
        analysis_protocol={
            "sample_size_rationale": "A sufficiently detailed design justification.",
            "readout_at": "9999-12-31T12:00:00Z",
        },
    )
    with pytest.raises(SchemaError):
        ExperimentDocument.model_validate(doc)

    doc["analysis_protocol"]["sample_size_rationale"] += "\x00"
    with pytest.raises(SchemaError):
        ExperimentDocument.model_validate(doc)


def test_prepared_unpaid_cancellation_has_negative_contribution(analytics):
    from world_model.restaurant_commerce.payments import CashAtPickupPaymentProvider

    data = analytics()
    target = next(r for r in data["rows"] if not r["order_id"])
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        svc = RestaurantCommerceService(
            s,
            verified_customer_id=target["customer_id"],
            payment_providers={"cash_at_pickup": CashAtPickupPaymentProvider()},
        )
        req = request(svc)
        req.customer.phone = s.get(Customer, target["customer_id"]).phone
        req.payment_provider = "cash_at_pickup"
        order = svc.create_order(BID, req)
        for state in ["accepted", "preparing", "ready", "cancelled"]:
            order = svc.transition_order(order.id, state)
        missing = report(s, BID, data["experiment_id"])
        assert missing["missing_orders"]["total"] == 1
        write_cost(s, order.id, variable=1000)
        after = report(s, BID, data["experiment_id"])
        old = next(a for a in before["arms"] if a["variant_id"] == target["variant_id"])
        new = next(a for a in after["arms"] if a["variant_id"] == target["variant_id"])
        assert (
            Fraction(new["profit_per_assigned_minor"])
            == Fraction(old["profit_per_assigned_minor"]) - 250
        )
        assert new["nonbuyers"] == old["nonbuyers"]
        assert "payment_inconsistency" not in after["warnings"]


def test_historical_full_refund_revises_receipts_and_preserves_expenses(analytics):
    data = analytics()
    target = next(r for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        svc = RestaurantCommerceService(s)
        order = svc.order_out(target["order_id"])
        svc.apply_payment_status(order.payments[0].provider_reference, "refunded")
        missing = report(s, BID, data["experiment_id"])
        assert missing["missing_orders"]["total"] == 1
        write_cost(s, order.id, variable=500, reward=100)
        after = report(s, BID, data["experiment_id"])
        old = next(a for a in before["arms"] if a["variant_id"] == target["variant_id"])
        new = next(a for a in after["arms"] if a["variant_id"] == target["variant_id"])
        assert int(new["net_revenue_minor"]) == int(old["net_revenue_minor"]) - order.total_minor
        assert Fraction(new["profit_per_assigned_minor"]) == Fraction(
            old["profit_per_assigned_minor"]
        ) - Fraction(target["profit"] + 600, 4)


def test_new_version_does_not_rewrite_run_window_or_protocol(analytics):
    data = analytics()
    with data["factory"]() as s:
        cfg = LoyaltyConfigurationService(s, "new-proposal")
        current = cfg.get("experiments", BID, data["experiment_id"])
        doc = dict(current["document"])
        doc["observation_days"] = 90
        doc["analysis_protocol"] = {
            **doc["analysis_protocol"],
            "readout_at": data["clock"] + timedelta(days=92),
        }
        edited = cfg.edit(
            "experiments",
            BID,
            data["experiment_id"],
            ExperimentEdit(
                expected_revision=current["revision"],
                document=ExperimentDocument.model_validate(doc),
            ),
        )
        publish(cfg, edited, "experiments")
        result = report(s, BID, data["experiment_id"])
        assert result["observation_days"] == 30
        assert result["experiment_version_id"] == data["version_id"]


def test_cross_group_overlap_is_reported_without_dropping_customer(analytics):
    data = analytics()
    target = data["rows"][0]
    with data["factory"]() as s:
        other = experiment_version(s, data["program_version"], exclusion_group="other-promotion")
        assert enroll(s, other, target["customer_id"])["eligible"]
        s.commit()
        result = report(s, BID, data["experiment_id"])
        assert "experiment_contamination" in result["warnings"]
        assert sum(a["contaminated_customers"] for a in result["arms"]) == 1
        assert result["assigned_customers"] == 8


def test_outside_window_exposure_is_separate_and_revision_changes(analytics):
    data = analytics()
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        a = s.get(LoyaltyAssignment, data["rows"][0]["assignment_id"])
        s.add(
            LoyaltyAssignmentExposure(
                business_id=BID,
                customer_id=a.customer_id,
                assignment_id=a.id,
                kind="control_surface_rendered"
                if a.strategy_version_id is None
                else "offer_surface_rendered",
                surface="synthetic",
                source_ref="late-observation",
                warnings_json='["outside_offer_window"]',
                actor_id="synthetic",
                observed_at=a.evaluation_ends_at + timedelta(days=1),
            )
        )
        s.commit()
        after = report(s, BID, data["experiment_id"])
        assert after["exposures_outside_followup"] == 1
        assert sum(a["exposed_customers"] for a in after["arms"]) == 0
        assert before["data_revision"] != after["data_revision"]


def test_repeat_denominators_and_purchase_before_assignment(analytics):
    data = analytics()
    target = next(r for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        svc = RestaurantCommerceService(s, verified_customer_id=target["customer_id"])
        req = request(svc)
        req.customer.phone = s.get(Customer, target["customer_id"]).phone
        later = pay_and_complete(svc, svc.create_order(BID, req))
        a = s.get(LoyaltyAssignment, target["assignment_id"])
        order = s.get(Order, later.id)
        order.created_at = order.completed_at = a.assigned_at + timedelta(days=35)
        s.commit()
        result = report(s, BID, data["experiment_id"])
        arm = next(v for v in result["arms"] if v["variant_id"] == a.variant_id)
        assert arm["repeat_purchase"]["30"]["repeat_customers"] == 0
        assert arm["repeat_purchase"]["60"]["repeat_customers"] == 1
        assert arm["repeat_purchase"]["60"]["eligible_assigned"] == 4
        # A checkout initiated before randomization cannot become a new purchase
        # outcome just because it completes later.
        original = s.get(Order, target["order_id"])
        original.created_at = a.assigned_at - timedelta(days=1)
        s.commit()
        after = report(s, BID, data["experiment_id"])
        reduced = next(v for v in after["arms"] if v["variant_id"] == a.variant_id)
        assert reduced["purchase_count"] == arm["purchase_count"] - 1


def test_large_money_and_unknown_currency_are_not_floating_totals(analytics):
    data = analytics()
    maximum = 2**53 - 1
    with data["factory"]() as s:
        for target in data["rows"]:
            if target["order_id"]:
                write_cost(s, target["order_id"], variable=maximum, reward=maximum)
        result = report(s, BID, data["experiment_id"])
        for arm in result["arms"]:
            expected = Fraction(int(arm["net_revenue_minor"]) - 4 * maximum - 400, 4)
            assert arm["profit_per_assigned_minor"] == decimal(expected)
        oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
        s.get(Order, oid).currency = "USD"
        s.scalar(select(Payment).where(Payment.order_id == oid)).currency = "USD"
        s.commit()
        changed = report(s, BID, data["experiment_id"])
        assert "currency_mismatch" in changed["warnings"]
        assert any(a["revenue_per_assigned_minor"] is None for a in changed["arms"])


def test_sqlite_replace_cannot_rewrite_append_only_evidence(analytics):
    data = analytics()
    if data["factory"].kw["bind"].dialect.name != "sqlite":
        return  # PostgreSQL has no INSERT OR REPLACE operation.
    with data["factory"]() as s:
        row = s.scalar(select(LoyaltyFinancialEvidence))
        columns = list(LoyaltyFinancialEvidence.__table__.columns.keys())
        values = ["'tampered'" if c == "source_ref" else c for c in columns]
        with pytest.raises(DBAPIError):
            s.execute(
                text(
                    f"INSERT OR REPLACE INTO {TABLE} ({','.join(columns)}) "
                    f"SELECT {','.join(values)} FROM {TABLE} WHERE id=:id"
                ),
                {"id": row.id},
            )
        s.rollback()


def test_csv_escapes_variant_formulas(analytics):
    import csv
    import io

    data = analytics()
    with data["factory"]() as s:
        result = report(s, BID, data["experiment_id"])
        result["arms"][0]["name"] = '=HYPERLINK("https://invalid.example")'
        rows = list(csv.reader(io.StringIO(csv_report(result))))
        assert rows[3][0].startswith("'=")


def test_operating_evidence_invalidates_when_assignment_population_grows(analytics):
    data = analytics()
    with data["factory"]() as s:
        cid = str(uuid4())
        s.add(Customer(id=cid, business_id=BID, name="new nonbuyer", phone="3006999999"))
        s.commit()
        added = enroll(s, data["version_id"], cid)["assignment"]
        s.commit()
        result = report(s, BID, data["experiment_id"])
        arm = next(a for a in result["arms"] if a["variant_id"] == added["variant_id"])
        assert arm["assigned_customers"] == 5
        assert arm["profit_per_assigned_minor"] is None
        assert arm["missing_operating_cost"]
        write_operating(s, arm["variant_id"], 400)
        fixed = report(s, BID, data["experiment_id"])
        assert (
            next(a for a in fixed["arms"] if a["variant_id"] == arm["variant_id"])[
                "profit_per_assigned_minor"
            ]
            is not None
        )


def test_report_snapshot_cannot_mix_concurrent_cost_revisions(analytics):
    data = analytics()
    engine = data["factory"].kw["bind"]
    oid = next(r["order_id"] for r in data["rows"] if r["order_id"])
    fired = []
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])

        def update_after_orders(_conn, _cursor, statement, *_args):
            if not fired and "FROM restaurant_orders" in statement:
                fired.append(True)
                with data["factory"]() as writer:
                    write_cost(writer, oid, variable=1)

        event.listen(engine, "after_cursor_execute", update_after_orders)
        try:
            during = report(s, BID, data["experiment_id"])
        finally:
            event.remove(engine, "after_cursor_execute", update_after_orders)
        assert fired
        assert during["data_revision"] == before["data_revision"]
        assert during["arms"] == before["arms"]
        assert report(s, BID, data["experiment_id"])["data_revision"] != before["data_revision"]


def test_baseline_redemption_reopens_accrual_review_and_discount_counts_once(analytics):
    from world_model.restaurant_commerce.models import RewardDefinition

    data = analytics()
    target = next(r for r in data["rows"] if r["order_id"])
    with data["factory"]() as s:
        before = report(s, BID, data["experiment_id"])
        old_cost = context(s, BID, "orders", target["order_id"])["latest"]["document"]
        reward = RewardDefinition(
            business_id=BID,
            name="synthetic fixed discount",
            points_cost=1,
            discount_minor=1000,
            minimum_order_minor=0,
        )
        s.add(reward)
        s.commit()
        svc = RestaurantCommerceService(s, verified_customer_id=target["customer_id"])
        req = request(svc)
        req.customer.phone = s.get(Customer, target["customer_id"]).phone
        req.reward_id = reward.id
        order = pay_and_complete(svc, svc.create_order(BID, req))
        assert order.reward_discount_minor == 1000
        write_cost(s, order.id, variable=500, reward=200)
        pending = report(s, BID, data["experiment_id"])
        assert pending["missing_orders"]["total"] == 1
        assert pending["missing_orders"]["items"][0]["order_id"] == target["order_id"]
        write_cost(
            s,
            target["order_id"],
            variable=old_cost["variable_cost_minor"],
            reward=old_cost["additional_reward_cost_minor"],
        )
        after = report(s, BID, data["experiment_id"])
        original = next(a for a in before["arms"] if a["variant_id"] == target["variant_id"])
        current = next(a for a in after["arms"] if a["variant_id"] == target["variant_id"])
        assert Fraction(current["profit_per_assigned_minor"]) == Fraction(
            original["profit_per_assigned_minor"]
        ) + Fraction(order.total_minor - 700, 4)


def test_measurement_requires_explicit_upgrade_and_optional_statistics(factory, monkeypatch):
    engine = factory.kw["bind"]
    assert not inspect(engine).has_table(TABLE)
    with pytest.raises(RuntimeError, match="offline upgrade"):
        create_app(
            engine=engine,
            loyalty_configuration_enabled=True,
            loyalty_analytics_enabled=True,
        )
    with monkeypatch.context() as m:
        import sys

        m.setitem(sys.modules, "scipy.stats", None)
        create_app(
            engine=engine,
            loyalty_configuration_enabled=True,
            loyalty_analytics_enabled=False,
        )
        with pytest.raises(RuntimeError, match="loyalty-analytics extra"):
            create_app(
                engine=engine,
                loyalty_configuration_enabled=True,
                loyalty_analytics_enabled=True,
            )
    monkeypatch.setenv("COMMERCE_LOYALTY_ANALYTICS_ENABLED", "yes")
    with pytest.raises(RuntimeError, match="must be 0 or 1"):
        create_app(engine=engine)


def test_synthetic_demo_preserves_cost_corrections_on_restart(tmp_path):
    from world_model.restaurant_commerce.campaign_demo import BUSINESS
    from world_model.restaurant_commerce.loyalty_analytics_demo import app_for_demo
    from world_model.restaurant_commerce.loyalty_models import LoyaltyExperiment

    url = "sqlite:///" + str(tmp_path / "synthetic-analytics.db")
    app = app_for_demo(url)
    with app.state.session_factory() as s:
        eid = s.scalar(
            select(LoyaltyExperiment.id).where(
                LoyaltyExperiment.request_key == "synthetic-profit-analysis-v1"
            )
        )
        result = report(s, BUSINESS, eid)
        assert result["assigned_customers"] == 40
        assert result["mature_customers"] == 0
        assert not result["primary_evaluation_complete"]
        assert sum(a["nonbuyers"] for a in result["arms"]) >= 30
        oid = result["cost_orders"]["items"][0]["order_id"]
        current = context(s, BUSINESS, "orders", oid)
        record(
            s,
            BUSINESS,
            "orders",
            oid,
            OrderCosts(
                request_key="synthetic-operator-correction",
                expected_revision=current["latest"]["revision"],
                financial_digest=current["financial_digest"],
                source_ref="synthetic operator invoice",
                includes_estimate=False,
                variable_cost_minor=1234,
                additional_reward_cost_minor=200,
            ),
            "synthetic-finance",
        )
        count = s.scalar(select(func.count()).select_from(LoyaltyFinancialEvidence))
    again = app_for_demo(url)
    with again.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(LoyaltyFinancialEvidence)) == count
        assert (
            context(s, BUSINESS, "orders", oid)["latest"]["document"]["variable_cost_minor"] == 1234
        )
    app.state.session_factory.kw["bind"].dispose()
    again.state.session_factory.kw["bind"].dispose()
