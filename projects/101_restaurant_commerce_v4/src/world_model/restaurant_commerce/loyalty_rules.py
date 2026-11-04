"""Pure, versioned reward arithmetic. No database, clock, wallet or provider writes.

Inputs describe a hypothetical, already-priced cart. Subtotals exclude tax/delivery;
existing promotion discounts are supplied per line, never allocated speculatively.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .errors import ValidationError
from .loyalty_schemas import Money, StrategyDocument, Strict

CALCULATION_VERSION = "points-fixed-v1"
MAX_MONEY = 2**53 - 1
MAX_POINTS = 2**31 - 1
Points = Annotated[int, Field(strict=True, ge=0, le=MAX_POINTS)]
Identifier = Annotated[str, Field(min_length=1, max_length=64)]


class PreviewLine(Strict):
    line_id: Identifier
    product_id: Identifier
    subtotal_minor: Money
    promotion_discount_minor: Money = 0

    @model_validator(mode="after")
    def valid_discount(self):
        if self.promotion_discount_minor > self.subtotal_minor:
            raise ValueError("Line promotion discount cannot exceed item subtotal")
        return self


class PreviewScenario(Strict):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    at: datetime
    lines: list[PreviewLine] = Field(max_length=200)
    customer_id: Identifier | None = None
    assume_verified_identity: bool = Field(default=False, strict=True)
    assumed_available_points: Points = 0
    assumed_refund_debt_points: Points = 0
    redeem_reward: bool = Field(default=False, strict=True)
    tax_minor: Money = 0
    delivery_fee_minor: Money = 0

    @model_validator(mode="after")
    def valid_scenario(self):
        if self.at.utcoffset() is None:
            raise ValueError("Scenario time must include a timezone")
        try:
            self.at = self.at.astimezone(UTC)
        except OverflowError as exc:
            raise ValueError("Scenario time exceeds the supported UTC date range") from exc
        if len({line.line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Scenario line IDs must be unique")
        if self.assume_verified_identity and self.customer_id is None:
            raise ValueError("A verified-identity assumption requires a customer ID")
        total = sum(line.subtotal_minor for line in self.lines)
        if total + self.tax_minor + self.delivery_fee_minor > MAX_MONEY:
            raise ValueError("Scenario total exceeds the supported minor-unit range")
        return self


class PreviewLineResult(Strict):
    line_id: str
    product_id: str
    net_item_minor: Money
    included: bool
    exclusion_reason: str | None
    reward_discount_minor: Money = 0
    earning_basis_minor: Money = 0


class EarningResult(Strict):
    configured: bool
    points: Points = 0
    spend_minor_per_point: int | None = None
    points_per_unit: int | None = None
    qualifying_units: int = 0
    remainder_minor: Money = 0
    expires_at: datetime | None = None
    reasons: list[str] = Field(default_factory=list)


class RedemptionResult(Strict):
    requested: bool
    eligible_by_rules: bool = False
    points_required: Points = 0
    points_spent: Points = 0
    discount_minor: Money = 0
    capped_by: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RulePreview(Strict):
    calculation_version: Literal["points-fixed-v1"] = CALCULATION_VERSION
    mode: Literal["hypothetical"] = "hypothetical"
    execution_enabled: Literal[False] = False
    budget_check: Literal["not_performed"] = "not_performed"
    activation_check: Literal["not_performed"] = "not_performed"
    supported: bool
    eligible_by_rules: bool
    reasons: list[str]
    currency: str
    at: datetime
    eligible_item_spend_minor_before_reward: Money
    eligible_item_spend_minor_after_reward: Money
    order_total_minor_before_reward: Money
    order_total_minor_after_reward: Money
    earning: EarningResult
    redemption: RedemptionResult
    lines: list[PreviewLineResult]
    warnings: list[str] = Field(
        default_factory=lambda: [
            "hypothetical_prices_identity_and_balance",
            "budget_availability_and_reservation_not_checked",
            "program_activation_not_checked",
            "no_reward_issued_or_redeemed",
        ]
    )


def allocate_discount(amount: int, weights: dict[str, int]) -> dict[str, int]:
    """Largest remainder, with stable line-ID ties; allocation always conserves money."""
    total = sum(weights.values())
    if not total or not amount:
        return dict.fromkeys(weights, 0)
    allocations = {key: amount * weight // total for key, weight in weights.items()}
    remaining = amount - sum(allocations.values())
    ranking = sorted(weights, key=lambda key: (-(amount * weights[key] % total), key))
    for key in ranking[:remaining]:
        allocations[key] += 1
    return allocations


def evaluate_rules(document: StrategyDocument, scenario: PreviewScenario) -> RulePreview:
    """Evaluate one published document at an explicit time, without current mutable rules.

    Minimum spend is assessed before the new reward, after prior promotions. Earning
    uses eligible spend after both promotions and the previewed fixed-value reward.
    Dates are [start,end). A failed redemption does not prevent otherwise valid earning.
    Monetary campaign budgets are intentionally not interpreted as point valuations.
    """
    policy = document.eligibility
    lines = []
    for line in sorted(scenario.lines, key=lambda item: item.line_id):
        reason = None
        if line.product_id in policy.excluded_product_ids:
            reason = "product_excluded"
        elif policy.included_product_ids and line.product_id not in policy.included_product_ids:
            reason = "product_not_included"
        net = line.subtotal_minor - line.promotion_discount_minor
        lines.append(
            PreviewLineResult(
                line_id=line.line_id,
                product_id=line.product_id,
                net_item_minor=net,
                included=reason is None,
                exclusion_reason=reason,
                earning_basis_minor=net if reason is None else 0,
            )
        )
    eligible_spend = sum(line.earning_basis_minor for line in lines)
    order_total = (
        sum(line.net_item_minor for line in lines)
        + scenario.tax_minor
        + scenario.delivery_fee_minor
    )
    reasons = []
    supported = document.reward is None or document.reward.type == "fixed_value"
    if not supported:
        reasons.append("unsupported_reward_type:" + document.reward.type)
    if scenario.currency != document.currency:
        reasons.append("currency_mismatch")
    if not scenario.assume_verified_identity or scenario.customer_id is None:
        reasons.append("verified_identity_required")
    if policy.customer_ids and scenario.customer_id not in policy.customer_ids:
        reasons.append("customer_not_included")
    if document.start_at is not None and scenario.at < document.start_at:
        reasons.append("program_not_started")
    if document.end_at is not None and scenario.at >= document.end_at:
        reasons.append("program_ended")
    if not document.stack_with_promotions and any(
        line.promotion_discount_minor for line in scenario.lines
    ):
        reasons.append("promotion_stacking_disallowed")
    if eligible_spend == 0:
        reasons.append("no_eligible_spend")
    if eligible_spend < policy.minimum_purchase_minor:
        reasons.append("minimum_purchase_not_met")

    redemption = RedemptionResult(requested=scenario.redeem_reward)
    reward = document.reward
    if scenario.redeem_reward:
        redemption.reasons.extend(reasons)
        if reward is None:
            redemption.reasons.append("no_redemption_rule")
        elif supported:
            redemption.points_required = max(document.minimum_redeem_points, reward.points_cost)
            if scenario.assumed_available_points < redemption.points_required:
                redemption.reasons.append("insufficient_points")
            if scenario.assumed_refund_debt_points:
                redemption.reasons.append("outstanding_refund_debt")
            amount = min(reward.discount_minor, document.maximum_reward_minor, eligible_spend)
            if amount == 0:
                redemption.reasons.append("zero_reward_value")
            if document.maximum_reward_minor < reward.discount_minor:
                redemption.capped_by.append("maximum_reward_minor")
            if eligible_spend < min(reward.discount_minor, document.maximum_reward_minor):
                redemption.capped_by.append("eligible_item_spend")
            if not redemption.reasons:
                redemption.eligible_by_rules = True
                redemption.discount_minor = amount
                redemption.points_spent = reward.points_cost
    else:
        redemption.reasons.append("redemption_not_requested")

    allocations = allocate_discount(
        redemption.discount_minor,
        {line.line_id: line.net_item_minor for line in lines if line.included},
    )
    for line in lines:
        line.reward_discount_minor = allocations.get(line.line_id, 0)
        line.earning_basis_minor -= line.reward_discount_minor
    earning_spend = eligible_spend - redemption.discount_minor
    earning = EarningResult(configured=document.earning is not None)
    if document.earning is None:
        earning.reasons.append("no_earning_rule")
    else:
        earning.spend_minor_per_point = document.earning.spend_minor_per_point
        earning.points_per_unit = document.earning.points_per_unit
        earning.reasons.extend(reasons)
        if not reasons:
            units, remainder = divmod(earning_spend, document.earning.spend_minor_per_point)
            points = units * document.earning.points_per_unit
            if points > MAX_POINTS:
                raise ValidationError("Calculated points exceed the supported account range")
            earning.qualifying_units = units
            earning.remainder_minor = remainder
            earning.points = points
            if points == 0:
                earning.reasons.append("below_earning_unit")
            elif document.expiration_days is not None:
                try:
                    earning.expires_at = scenario.at + timedelta(days=document.expiration_days)
                except OverflowError as exc:
                    raise ValidationError(
                        "Calculated expiration exceeds the supported date range"
                    ) from exc
    return RulePreview(
        supported=supported,
        eligible_by_rules=not reasons,
        reasons=reasons,
        currency=scenario.currency,
        at=scenario.at,
        eligible_item_spend_minor_before_reward=eligible_spend,
        eligible_item_spend_minor_after_reward=earning_spend,
        order_total_minor_before_reward=order_total,
        order_total_minor_after_reward=order_total - redemption.discount_minor,
        earning=earning,
        redemption=redemption,
        lines=lines,
    )
