"""Assignment -> optional incentive -> immutable order binding. Never enrolls at checkout."""

import json
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import select

from .errors import NotFoundError, ValidationError
from .loyalty_assignment import bounded
from .loyalty_assignment_migrations import installed
from .loyalty_assignment_models import (
    LoyaltyAssignment as Assignment,
)
from .loyalty_assignment_models import (
    LoyaltyAssignmentOrder as Binding,
)
from .loyalty_execution import ExecutionSelection, calculate
from .loyalty_execution_models import LoyaltyBudget
from .loyalty_models import LoyaltyExperiment, LoyaltyStrategy, LoyaltyStrategyVersion
from .loyalty_wallet import aware
from .models import Customer, utcnow


@dataclass(frozen=True)
class AssignmentCheckout:
    experiment_id: str
    redeem_reward: bool = False
    enabled: bool = False
    price_basis: str | None = None


@dataclass(frozen=True)
class AssignmentPlan:
    experiment_id: str
    assignment_id: str | None
    selected_at: datetime
    reason: str
    version_id: str | None = None


@dataclass(frozen=True)
class AssignmentChoice:
    plan: AssignmentPlan
    reason: str
    selection: ExecutionSelection | None = None
    details: tuple = ()


def validate_context(service):
    context = service.loyalty_experiment
    if context is None:
        return None
    if (
        not isinstance(context, AssignmentCheckout)
        or context.enabled is not True
        or context.price_basis != "synthetic_tax_exclusive"
    ):
        raise ValidationError(
            "Assignment checkout requires explicit synthetic enablement and price basis"
        )
    bounded(context.experiment_id, "experiment_id", 36)
    if type(context.redeem_reward) is not bool or service.loyalty_execution is not None:
        raise ValidationError("Choose one trusted loyalty selection source")
    if not installed(service.session):
        raise ValidationError("Offline loyalty assignment upgrade required")
    return context


def prepare_checkout(service, business_id, *, lock=False):
    context = validate_context(service)
    session = service.session
    experiment = session.get(LoyaltyExperiment, context.experiment_id)
    if experiment is None or experiment.business_id != business_id:
        raise NotFoundError("Experiment does not belong to this business")
    now = utcnow()
    if service.verified_customer_id is None:
        return AssignmentPlan(experiment.id, None, now, "unverified_identity")
    customer_query = select(Customer).where(
        Customer.id == service.verified_customer_id, Customer.business_id == business_id
    )
    if lock:
        customer_query = customer_query.with_for_update().execution_options(populate_existing=True)
    if session.scalar(customer_query) is None:
        raise ValidationError("Verified customer does not belong to this business")
    query = (
        select(LoyaltyExperiment)
        .where(LoyaltyExperiment.id == experiment.id)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    experiment = session.scalar(query)
    now = utcnow()  # Lock waits must not extend an expired offer window.
    row = session.scalar(
        select(Assignment).where(
            Assignment.business_id == business_id,
            Assignment.experiment_id == experiment.id,
            Assignment.customer_id == service.verified_customer_id,
        )
    )
    if row is None:
        return AssignmentPlan(experiment.id, None, now, "not_enrolled")
    if row.strategy_version_id is None:
        reason = "control"
    elif experiment.state in {"paused", "archived"}:
        reason = "experiment_paused_or_archived"
    elif not aware(row.assigned_at) <= now < aware(row.evaluation_ends_at):
        reason = "outside_offer_window"
    else:
        reason = "candidate"
    return AssignmentPlan(experiment.id, row.id, now, reason, row.strategy_version_id)


def quote_choice(service, business_id, items, discounts, *, currency, reward_id):
    plan = service._assignment_plan or prepare_checkout(service, business_id)
    if plan.reason != "candidate":
        return AssignmentChoice(plan, plan.reason)
    if reward_id:
        return AssignmentChoice(plan, "baseline_reward_priority")
    version = service.session.get(LoyaltyStrategyVersion, plan.version_id)
    if not version or version.business_id != business_id:
        raise ValidationError("Assigned program history is missing")
    parent = service.session.scalar(
        select(LoyaltyStrategy)
        .where(LoyaltyStrategy.id == version.strategy_id)
        .execution_options(populate_existing=True)
    )
    if parent.state in {"paused", "archived"}:
        return AssignmentChoice(plan, "program_paused_or_archived")
    selection = ExecutionSelection(
        plan.version_id,
        service.loyalty_experiment.redeem_reward,
        True,
        service.loyalty_experiment.price_basis,
    )
    version, rules, account, result = calculate(
        service,
        business_id,
        items,
        discounts.promotion_discount_minor,
        selection=selection,
        allow_historical=True,
        strict=False,
    )
    if rules.currency != currency:
        return AssignmentChoice(plan, "currency_mismatch")
    if not result.supported:
        raise ValidationError("Assigned program executor is unsupported")
    if not result.eligible_by_rules:
        return AssignmentChoice(plan, "offer_ineligible", details=tuple(result.reasons))
    details = ()
    if selection.redeem_reward and not result.redemption.eligible_by_rules:
        details = tuple(result.redemption.reasons)
        if rules.earning is None:
            return AssignmentChoice(plan, "redemption_unavailable", details=details)
        selection = replace(selection, redeem_reward=False)
        version, rules, account, result = calculate(
            service,
            business_id,
            items,
            discounts.promotion_discount_minor,
            selection=selection,
            allow_historical=True,
            strict=False,
        )
    amount = (
        result.earning.points * rules.estimated_cost_per_point_minor
        + result.redemption.discount_minor
    )
    buckets = {
        row.scope: row
        for row in service.session.scalars(
            select(LoyaltyBudget)
            .where(
                LoyaltyBudget.strategy_id == version.strategy_id,
                LoyaltyBudget.scope.in_(("*", service.verified_customer_id)),
            )
            .execution_options(populate_existing=True)
        )
    }
    for scope, cap in (
        ("*", rules.campaign_budget_minor),
        (service.verified_customer_id, rules.per_customer_budget_minor),
    ):
        row = buckets.get(scope)
        used = row.reserved_minor + row.committed_minor if row else 0
        if used + amount > cap:
            return AssignmentChoice(plan, "budget_exhausted")
    discounts.reward_discount_minor = result.redemption.discount_minor
    discounts.total_discount_minor += result.redemption.discount_minor
    discounts.reward_name = rules.name if result.redemption.discount_minor else None
    return AssignmentChoice(
        plan, "incremental_earning_only" if details else "incremental_selected", selection, details
    )


def bind_order(service, order):
    choice = service._assignment_choice
    if choice is None:
        raise ValidationError("Assignment checkout decision is missing")
    service.session.add(
        Binding(
            order_id=order.id,
            business_id=order.business_id,
            customer_id=order.customer_id,
            experiment_id=choice.plan.experiment_id,
            assignment_id=choice.plan.assignment_id,
            execution_order_id=order.id if choice.selection else None,
            reason=choice.reason,
            details_json=json.dumps(
                {"reasons": choice.details, "assigned_strategy_version_id": choice.plan.version_id},
                sort_keys=True,
            ),
            selected_at=choice.plan.selected_at,
        )
    )
    service.session.flush()


def validate_reservation(service):
    """Recheck time after wallet/budget lock waits, before any reward reservation."""
    plan = service._assignment_plan
    if plan is None:
        raise ValidationError("Assignment reservation context missing")
    row = service.session.get(Assignment, plan.assignment_id)
    if row is None or not aware(row.assigned_at) <= utcnow() < aware(row.evaluation_ends_at):
        raise ValidationError("Assignment offer window ended; obtain a new quote")
