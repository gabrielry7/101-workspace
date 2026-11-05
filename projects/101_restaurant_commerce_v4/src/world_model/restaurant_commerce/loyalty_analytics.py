"""Intent-to-treat outcomes from original assignments, including zero purchasers."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fractions import Fraction

from sqlalchemy import select

from .errors import NotFoundError
from .loyalty_assignment_models import (
    LoyaltyAssignment,
    LoyaltyAssignmentExposure,
    LoyaltyExperimentRun,
)
from .loyalty_execution_models import LoyaltyOrderSnapshot
from .loyalty_measurement_evidence import (
    describe,
    digest,
    latest_evidence,
    operating_digest,
    order_facts,
    verified,
)
from .loyalty_models import LoyaltyExperimentVariant, LoyaltyExperimentVersion
from .loyalty_read_snapshot import committed_snapshot
from .loyalty_statistics import decimal, welch_interval
from .models import LoyaltyAccount, LoyaltyLedgerEntry, Order, RewardRedemption, utcnow
from .staff import aware

REPORT_VERSION = "itt-contribution-v1"


def report(session, business_id, experiment_id):
    with committed_snapshot(session) as snapshot:
        return _report(snapshot, business_id, experiment_id)


def _report(session, business_id, experiment_id):
    now = utcnow()
    run = session.scalar(
        select(LoyaltyExperimentRun).where(
            LoyaltyExperimentRun.experiment_id == experiment_id,
            LoyaltyExperimentRun.business_id == business_id,
        )
    )
    version = session.scalar(
        select(LoyaltyExperimentVersion)
        .where(
            LoyaltyExperimentVersion.business_id == business_id,
            LoyaltyExperimentVersion.experiment_id == experiment_id,
            *(
                [LoyaltyExperimentVersion.id == run.experiment_version_id]
                if run
                else []
            ),
        )
        .order_by(LoyaltyExperimentVersion.revision.desc())
    )
    if version is None:
        raise NotFoundError("Published experiment not found")
    doc = json.loads(version.document)
    days, protocol = doc["observation_days"], doc.get("analysis_protocol")
    variants = session.scalars(
        select(LoyaltyExperimentVariant)
        .where(LoyaltyExperimentVariant.experiment_version_id == version.id)
        .order_by(LoyaltyExperimentVariant.id)
    ).all()
    assignments = session.scalars(
        select(LoyaltyAssignment)
        .where(
            LoyaltyAssignment.business_id == business_id,
            LoyaltyAssignment.experiment_version_id == version.id,
        )
        .order_by(LoyaltyAssignment.id)
    ).all()
    by_customer = {a.customer_id: a for a in assignments}
    warnings = {
        "observed_channels_only",
        "current_refunds_revise_window_orders",
        "no_automatic_winner",
    }
    if not run:
        warnings.add("experiment_not_enrolled")
    if not protocol:
        warnings.add("analysis_protocol_missing")
    if protocol and any(aware(a.assigned_at) < aware(version.published_at) for a in assignments):
        warnings.add("analysis_protocol_late")
    start = min((aware(a.assigned_at) for a in assignments), default=now)
    last_end = max(
        (aware(a.assigned_at) + timedelta(days=max(90, days)) for a in assignments),
        default=now,
    )
    orders = (
        session.scalars(
            select(Order).where(
                Order.business_id == business_id,
                Order.created_at >= start,
                Order.created_at < min(last_end, now),
            )
        ).all()
        if assignments
        else []
    )
    facts = order_facts(session, orders)
    evidence = latest_evidence(
        session,
        business_id,
        ["order:" + o.id for o in orders] + ["variant:" + v.id for v in variants],
    )
    purchases, financial_orders, unknown = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(set),
    )
    coverage = Counter()
    providers = set()
    missing_orders, observation_ids = [], []
    for order in orders:
        fact = facts[order.id]
        has_finance = (
            fact["gross_receipts_minor"] > 0
            or order.completed_at is not None
            or order.status == "cancelled"
        )
        if has_finance:
            coverage["observed_financial_orders"] += 1
            coverage[
                "verified_financial_orders"
                if verified(order)
                else "unverified_financial_orders"
            ] += 1
        a = by_customer.get(order.customer_id)
        if (
            not a
            or not verified(order)
            or aware(order.created_at) < aware(a.assigned_at)
        ):
            continue
        if order.completed_at and aware(order.completed_at) <= now:
            purchases[a.id].append(order)
        if aware(order.created_at) >= aware(a.evaluation_ends_at):
            continue
        completed_in_window = bool(
            order.completed_at
            and aware(order.completed_at) < aware(a.evaluation_ends_at)
            and aware(order.completed_at) <= now
        )
        cancelled_financial = order.status == "cancelled" and has_finance
        if not completed_in_window and not cancelled_financial:
            if has_finance or order.accepted_at is not None:
                unknown[a.id].add("unresolved_order_at_window")
            continue
        financial_orders[a.id].append(order)
        providers.update(fact["providers"])
        if order.currency != doc["currency"]:
            unknown[a.id].add("currency_mismatch")
        unknown[a.id].update(fact["flags"])
        row = evidence.get("order:" + order.id)
        if row:
            observation_ids.append(row.id)
        if row is None or row.financial_digest != fact["financial_digest"]:
            unknown[a.id].add("missing_or_stale_contribution")
            missing_orders.append(
                {
                    "order_id": order.id,
                    "order_code": order.public_code,
                    "variant_id": a.variant_id,
                    "currency": order.currency,
                    "financial_digest": fact["financial_digest"],
                    "latest": describe(row),
                    "stale": row is not None,
                }
            )
    if coverage["unverified_financial_orders"]:
        warnings.add("identity_coverage_incomplete")
    # Different exclusion groups can overlap without an explicit overlap row.
    overlap = set()
    other_assignments = (
        session.scalars(
            select(LoyaltyAssignment).where(
                LoyaltyAssignment.business_id == business_id,
                LoyaltyAssignment.experiment_id != experiment_id,
                LoyaltyAssignment.assigned_at <= now,
            )
        ).all()
        if assignments
        else []
    )
    for other in other_assignments:
        a = by_customer.get(other.customer_id)
        if (
            a
            and aware(a.assigned_at) < aware(other.exclusion_ends_at)
            and aware(other.assigned_at) < aware(a.exclusion_ends_at)
        ):
            overlap.add(a.id)
    if overlap:
        warnings.add("experiment_contamination")
    executions = (
        {
            r.order_id: r.version_id
            for r in session.scalars(
                select(LoyaltyOrderSnapshot)
                .join(Order, Order.id == LoyaltyOrderSnapshot.order_id)
                .where(Order.business_id == business_id, Order.created_at >= start)
            )
        }
        if assignments
        else {}
    )
    off_protocol = set()
    for a in assignments:
        if any(
            o.id in executions and executions[o.id] != a.strategy_version_id
            for o in financial_orders[a.id]
        ):
            off_protocol.add(a.id)
    if off_protocol:
        warnings.add("off_protocol_rewards")
    # Orderless credits cannot be silently treated as cost-free for a nonbuyer.
    orderless_events = []
    for entry, customer_id in session.execute(
        select(LoyaltyLedgerEntry, LoyaltyAccount.customer_id)
        .join(LoyaltyAccount, LoyaltyAccount.id == LoyaltyLedgerEntry.account_id)
        .where(
            LoyaltyAccount.business_id == business_id,
            LoyaltyLedgerEntry.order_id.is_(None),
            LoyaltyLedgerEntry.created_at >= start,
            LoyaltyLedgerEntry.created_at <= now,
        )
    ):
        a = by_customer.get(customer_id)
        if (
            a
            and aware(entry.created_at) < aware(a.evaluation_ends_at)
            and aware(entry.created_at) >= aware(a.assigned_at)
        ):
            unknown[a.id].add("unattributed_reward_cost")
            orderless_events.append(
                [entry.id, customer_id, entry.delta_points, entry.reason]
            )
    assignment_map = {a.id: a for a in assignments}
    exposure_events, exposed, late_exposures = [], set(), 0
    for receipt in session.scalars(
        select(LoyaltyAssignmentExposure)
        .join(
            LoyaltyAssignment,
            LoyaltyAssignment.id == LoyaltyAssignmentExposure.assignment_id,
        )
        .where(
            LoyaltyAssignment.experiment_version_id == version.id,
            LoyaltyAssignmentExposure.observed_at <= now,
        )
    ):
        a = assignment_map[receipt.assignment_id]
        exposure_events.append(
            [
                receipt.id,
                receipt.assignment_id,
                aware(receipt.observed_at).isoformat(),
                receipt.warnings_json,
            ]
        )
        if (
            aware(a.assigned_at)
            <= aware(receipt.observed_at)
            < aware(a.evaluation_ends_at)
        ):
            exposed.add(a.id)
        else:
            late_exposures += 1
        if json.loads(receipt.warnings_json):
            warnings.add("exposure_receipt_warnings")
    if late_exposures:
        warnings.add("exposures_outside_followup")
    applied = {
        r.order_id: r.points_spent
        for r in session.scalars(
            select(RewardRedemption).where(
                RewardRedemption.business_id == business_id,
                RewardRedemption.applied_at.is_not(None),
            )
        )
    }
    samples, arms = {}, []
    for variant in variants:
        members = [a for a in assignments if a.variant_id == variant.id]
        n = len(members)
        operating = evidence.get("variant:" + variant.id)
        op_digest = operating_digest(assignments, variant.id)
        op_known = operating is not None and operating.financial_digest == op_digest
        if operating:
            observation_ids.append(operating.id)
        op = json.loads(operating.document) if operating else {}
        if n and not op_known:
            warnings.add("missing_or_stale_operating_cost")
        values, arm_orders = [], []
        purchases_count, buyers, matured = 0, 0, 0
        repeats = {}
        estimated_cost_orders = 0
        for a in members:
            matured += aware(a.evaluation_ends_at) <= now
            qualifying = [
                o
                for o in purchases[a.id]
                if aware(o.created_at) < aware(a.evaluation_ends_at)
                and aware(o.completed_at) < aware(a.evaluation_ends_at)
            ]
            purchases_count += len(qualifying)
            buyers += bool(qualifying)
            selected = financial_orders[a.id]
            arm_orders.extend(selected)
            contribution = 0
            for order in selected:
                row = evidence.get("order:" + order.id)
                if row and row.financial_digest == facts[order.id]["financial_digest"]:
                    cost = json.loads(row.document)
                    estimated_cost_orders += bool(cost["includes_estimate"])
                    contribution += (
                        facts[order.id]["net_revenue_minor"]
                        - cost["variable_cost_minor"]
                        - cost["additional_reward_cost_minor"]
                    )
            values.append(
                Fraction(contribution)
                - Fraction(op.get("operating_cost_minor", 0), n or 1)
                if not unknown[a.id] and op_known
                else None
            )
        for period in (30, 60, 90):
            eligible = [
                a
                for a in members
                if aware(a.assigned_at) + timedelta(days=period) <= now
            ]
            repeat = sum(
                sum(
                    aware(o.created_at) < aware(a.assigned_at) + timedelta(days=period)
                    and aware(o.completed_at)
                    < aware(a.assigned_at) + timedelta(days=period)
                    for o in purchases[a.id]
                )
                >= 2
                for a in eligible
            )
            repeats[str(period)] = {
                "eligible_assigned": len(eligible),
                "repeat_customers": repeat,
                "rate": decimal(Fraction(repeat, len(eligible))) if eligible else None,
            }
        all_known = n > 0 and all(v is not None for v in values)
        samples[variant.id] = values if all_known else None
        arm_warnings = sorted({flag for a in members for flag in unknown[a.id]})
        warnings.update(arm_warnings)
        if estimated_cost_orders or op.get("includes_estimate"):
            warnings.add("financial_costs_include_estimates")
        if matured < n:
            warnings.add("incomplete_observation_windows")
        net = sum(facts[o.id]["net_revenue_minor"] for o in arm_orders)
        currency_known = not any("currency_mismatch" in unknown[a.id] for a in members)
        points_issued = sum(
            max(0, delta)
            for o in arm_orders
            for _, delta, reason in facts[o.id]["ledger"]
            if reason in {"order.completed", "loyalty.earned"}
        )
        outstanding = sum(
            Fraction(lot[3] * lot[5] * lot[6], 10000)
            for o in arm_orders
            for lot in facts[o.id]["lots"]
        )
        arms.append(
            {
                "variant_id": variant.id,
                "name": variant.name,
                "control": variant.strategy_version_id is None,
                "allocation_bps": variant.allocation_bps,
                "assigned_customers": n,
                "mature_customers": matured,
                "nonbuyers": n - buyers,
                "buyers": buyers,
                "purchase_count": purchases_count,
                "purchase_frequency": decimal(Fraction(purchases_count, n))
                if n
                else None,
                "net_revenue_minor": str(net) if currency_known else None,
                "revenue_per_assigned_minor": decimal(Fraction(net, n))
                if n and currency_known
                else None,
                "profit_per_assigned_minor": decimal(sum(values) / n)
                if all_known
                else None,
                "contribution_profit_minor": decimal(sum(values))
                if all_known
                else None,
                "missing_contribution_customers": sum(
                    bool(unknown[a.id]) for a in members
                ),
                "missing_operating_cost": not op_known,
                "estimated_cost_orders": estimated_cost_orders,
                "operating_cost_minor": str(op["operating_cost_minor"])
                if op_known
                else None,
                "operating_evidence": {
                    "financial_digest": op_digest,
                    "latest": describe(operating),
                },
                "exposed_customers": sum(a.id in exposed for a in members),
                "contaminated_customers": sum(
                    a.id in overlap or a.id in off_protocol for a in members
                ),
                "issued_points": str(points_issued),
                "redeemed_points": str(sum(applied.get(o.id, 0) for o in arm_orders)),
                "estimated_outstanding_cost_minor": decimal(outstanding),
                "repeat_purchase": repeats,
                "warnings": arm_warnings,
            }
        )
    if len(providers) > 1 and "simulated" in providers:
        warnings.add("mixed_simulated_and_other_payments")
    minimum = protocol["minimum_customers_per_arm"] if protocol else 100
    if any(a["assigned_customers"] < minimum for a in arms):
        warnings.add("insufficient_sample_size")
    readout_reached = bool(
        protocol and aware(datetime.fromisoformat(protocol["readout_at"])) <= now
    )
    if protocol and not readout_reached:
        warnings.add("scheduled_readout_not_reached")
    if aware(datetime.fromisoformat(doc["enrollment_end"])) > now:
        warnings.add("enrollment_still_open")
    allocation_p = None
    total = len(assignments)
    expected = [Fraction(total * a["allocation_bps"], 10000) for a in arms]
    if expected and min(expected) >= 5:
        from scipy.stats import chi2

        statistic = sum(
            (a["assigned_customers"] - e) ** 2 / e
            for a, e in zip(arms, expected, strict=True)
        )
        allocation_p = str(float(chi2.sf(float(statistic), len(arms) - 1)))
        if float(allocation_p) < 0.001:
            warnings.add("allocation_imbalance")
    else:
        warnings.add("allocation_diagnostic_unavailable")
    blocked = warnings & {
        "analysis_protocol_late",
        "analysis_protocol_missing",
        "incomplete_observation_windows",
        "insufficient_sample_size",
        "scheduled_readout_not_reached",
        "enrollment_still_open",
        "experiment_contamination",
        "off_protocol_rewards",
        "allocation_imbalance",
        "allocation_diagnostic_unavailable",
        "mixed_simulated_and_other_payments",
        "identity_coverage_incomplete",
        "financial_review_open",
        "unresolved_order_at_window",
        "currency_mismatch",
        "payment_inconsistency",
        "unattributed_reward_cost",
        "missing_or_stale_contribution",
        "missing_or_stale_operating_cost",
    }
    control = next(a for a in arms if a["control"])
    comparisons = []
    for arm in arms:
        if arm["control"]:
            continue
        x, y = samples[arm["variant_id"]], samples[control["variant_id"]]
        effect = (
            sum(x) / len(x) - sum(y) / len(y)
            if x is not None and y is not None
            else None
        )
        interval = (
            welch_interval(x, y, protocol["confidence_bps"], len(arms) - 1)
            if not blocked and effect is not None
            else None
        )
        reasons = set(blocked)
        if effect is None:
            reasons.add("missing_financial_evidence")
        elif not blocked and interval is None:
            reasons.add("zero_observed_variance")
        comparisons.append(
            {
                "variant_id": arm["variant_id"],
                "control_variant_id": control["variant_id"],
                "incremental_profit_per_assigned_minor": decimal(effect)
                if effect is not None
                else None,
                "confidence_interval": interval,
                "suppression_reasons": sorted(reasons),
            }
        )
    cost_orders = [
        {
            "order_id": o.id,
            "order_code": o.public_code,
            "variant_id": a.variant_id,
            "currency": o.currency,
            "financial_digest": facts[o.id]["financial_digest"],
            "latest": describe(evidence.get("order:" + o.id)),
            "stale": bool(
                evidence.get("order:" + o.id)
                and evidence["order:" + o.id].financial_digest
                != facts[o.id]["financial_digest"]
            ),
        }
        for a in assignments
        for o in financial_orders[a.id]
    ]
    revision = digest(
        {
            "version": version.digest,
            "assignments": [a.id for a in assignments],
            "financial_facts": sorted(
                [oid, f["financial_digest"]] for oid, f in facts.items()
            ),
            "evidence": sorted(observation_ids),
            "orderless_events": sorted(orderless_events),
            "overlap": sorted(overlap),
            "off_protocol": sorted(off_protocol),
            "exposures": sorted(exposure_events),
        }
    )
    return {
        "report_version": REPORT_VERSION,
        "as_of": now.isoformat(),
        "data_revision": revision,
        "experiment_id": experiment_id,
        "experiment_version_id": version.id,
        "configuration_digest": version.digest,
        "name": doc["name"],
        "currency": doc["currency"],
        "run_exists": run is not None,
        "primary_metric": doc["primary_metric"],
        "observation_days": days,
        "analysis_protocol": protocol,
        "enrollment_start": doc["enrollment_start"],
        "enrollment_end": doc["enrollment_end"],
        "first_assignment_at": start.isoformat() if assignments else None,
        "assigned_customers": total,
        "mature_customers": sum(a["mature_customers"] for a in arms),
        "arms": arms,
        "comparisons": comparisons,
        "primary_evaluation_complete": not blocked
        and all(c["confidence_interval"] is not None for c in comparisons),
        "coverage": dict(coverage),
        "allocation_diagnostic_p": allocation_p,
        "exposures_outside_followup": late_exposures,
        "financial_scope": "current_confirmed_refunds_for_orders_in_original_followup",
        "uncertainty_scope": "customer_variation_conditional_on_supplied_costs",
        "cost_basis": "net_receipts_less_variable_and_additional_loyalty_accrual_costs_v1",
        "historical_financial_cutoff_available": False,
        "automatic_winner": None,
        "missing_orders": {
            "total": len(missing_orders),
            "items": missing_orders[:100],
            "truncated": len(missing_orders) > 100,
        },
        "cost_orders": {
            "total": len(cost_orders),
            "items": cost_orders[:100],
            "truncated": len(cost_orders) > 100,
        },
        "warnings": sorted(warnings),
    }
