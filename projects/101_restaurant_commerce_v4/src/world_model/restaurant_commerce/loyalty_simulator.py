"""Pure, bounded reward economics. No wallet writes or estimated causal effects.

Money inputs are integer minor units. Fraction retains exact arithmetic through the
whole model; rounding happens only when rendering output. JSON money is returned as
integer strings so large aggregate amounts survive browser parsing without loss.
"""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from .loyalty_config import canonical, digest
from .loyalty_schemas import Bps, Money, Strict

SIMULATION_VERSION = "loyalty-economics-v1"
LIMIT = 2**53 - 1
SignedMoney = Annotated[int, Field(strict=True, ge=-LIMIT, le=LIMIT)]
Lift = Annotated[int, Field(strict=True, ge=-10000, le=100000)]
SignedMargin = Annotated[int, Field(strict=True, ge=-10000, le=10000)]


def exact_decimal(value):
    # Reject binary floats, booleans, exponent strings and unbounded representations.
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,7}(?:\.\d{1,6})?", value):
        raise ValueError("Use a nonnegative decimal string with at most six decimal places")
    return Decimal(value)


Frequency = Annotated[Decimal, BeforeValidator(exact_decimal), Field(ge=0, le=1000000)]


class MarginAssumption(Strict):
    type: Literal["margin"] = "margin"
    contribution_margin_bps: SignedMargin


class ContributionOrder(Strict):
    revenue_minor: Money
    contribution_minor: SignedMoney

    @model_validator(mode="after")
    def valid_contribution(self):
        if self.contribution_minor > self.revenue_minor:
            raise ValueError("Contribution cannot exceed this order's revenue")
        return self


class OrderContributions(Strict):
    type: Literal["order_contributions"]
    source_reference: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]+$")
    orders: list[ContributionOrder] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def positive_revenue(self):
        if sum(order.revenue_minor for order in self.orders) == 0:
            raise ValueError("Observed contribution requires positive aggregate order revenue")
        return self


class ProportionalReward(Strict):
    type: Literal["proportional"]
    reward_value_bps: Bps
    fulfillment_cost_bps: Bps


class PerPurchaseReward(Strict):
    type: Literal["per_purchase"]
    reward_value_minor: Money
    fulfillment_cost_minor: Money
    rewards_per_purchase: Frequency


class FixedIssuanceReward(Strict):
    type: Literal["fixed_issuance"]
    reward_value_minor: Money
    fulfillment_cost_minor: Money
    issued_rewards: Annotated[int, Field(strict=True, ge=0, le=10**9)]


class Sensitivity(Strict):
    redemption_bps: list[Bps] = Field(
        default_factory=lambda: [2500, 5000, 10000], min_length=1, max_length=9
    )
    lift_bps: list[Lift] = Field(default_factory=lambda: [0, 500, 1000], min_length=1, max_length=9)

    @model_validator(mode="after")
    def unique_axes(self):
        if len(set(self.redemption_bps)) != len(self.redemption_bps):
            raise ValueError("Redemption sensitivity values must be unique")
        if len(set(self.lift_bps)) != len(self.lift_bps):
            raise ValueError("Lift sensitivity values must be unique")
        return self


class SimulationScenario(Strict):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    horizon_days: Annotated[int, Field(strict=True, ge=1, le=3650)]
    average_order_value_minor: Money
    purchases_per_customer: Frequency
    customer_count: Annotated[int, Field(strict=True, ge=0, le=10**9)]
    contribution: Annotated[MarginAssumption | OrderContributions, Field(discriminator="type")]
    reward: Annotated[
        ProportionalReward | PerPurchaseReward | FixedIssuanceReward,
        Field(discriminator="type"),
    ]
    expected_redemption_bps: Bps
    operating_cost_minor: Money
    assumed_purchase_lift_bps: Lift
    sensitivity: Sensitivity = Field(default_factory=Sensitivity)


# Output money strings preserve large minor-unit integers in JSON clients.
Amount = Annotated[str, Field(pattern=r"^-?\d+$")]


class BreakEven(Strict):
    status: Literal["covered_at_zero_lift", "finite", "no_finite_break_even", "zero_baseline"]
    incremental_sales_minor: Amount | None
    required_lift_percent: str | None
    effective_incremental_margin_percent: str


class Projection(Strict):
    assumed_purchase_lift_bps: int
    expected_redemption_bps: int
    expected_orders: str
    projected_sales_minor: Amount
    expected_issued_face_value_minor: Amount
    expected_redeemed_face_value_minor: Amount
    expected_reward_cost_minor: Amount
    reward_cost_percent_of_sales: str | None
    incremental_contribution_before_costs_minor: Amount
    estimated_incremental_contribution_profit_minor: Amount
    profitable_under_assumptions: bool
    break_even: BreakEven
    warnings: list[str]


class SimulationResult(Strict):
    calculation_version: str = SIMULATION_VERSION
    scenario_digest: str
    scenario: SimulationScenario
    baseline_orders: str
    baseline_sales_minor: Amount
    baseline_contribution_minor: Amount
    contribution_margin_percent: str
    projection: Projection
    sensitivity: list[Projection]
    lift_is_assumed: Literal[True] = True
    causal_effect_estimated: Literal[False] = False
    money_encoding: Literal["integer_minor_unit_strings"] = "integer_minor_unit_strings"
    rounding: Literal["half_away_from_zero; break_even_sales_and_lift_ceil"] = (
        "half_away_from_zero; break_even_sales_and_lift_ceil"
    )
    assumptions: list[str]


def rounded(value: Fraction, places=0, *, ceiling=False):
    scaled = value * 10**places
    if ceiling:
        integer = -(-scaled.numerator // scaled.denominator)
    else:
        magnitude = abs(scaled)
        integer = (2 * magnitude.numerator + magnitude.denominator) // (2 * magnitude.denominator)
        if scaled < 0:
            integer = -integer
    sign = "-" if integer < 0 else ""
    digits = str(abs(integer)).zfill(places + 1)
    return sign + (digits if places == 0 else digits[:-places] + "." + digits[-places:])


def simulate(scenario: SimulationScenario) -> SimulationResult:
    orders = Fraction(scenario.purchases_per_customer) * scenario.customer_count
    sales = orders * scenario.average_order_value_minor
    contribution = scenario.contribution
    if isinstance(contribution, MarginAssumption):
        margin = Fraction(contribution.contribution_margin_bps, 10000)
    else:
        margin = Fraction(
            sum(o.contribution_minor for o in contribution.orders),
            sum(o.revenue_minor for o in contribution.orders),
        )
    reward = scenario.reward
    # Separate variable per-order cost from a fixed campaign issuance pool.
    fixed_face = fixed_cost = Fraction(0)
    if isinstance(reward, ProportionalReward):
        face_per_order = Fraction(
            scenario.average_order_value_minor * reward.reward_value_bps, 10000
        )
        cost_per_order = Fraction(
            scenario.average_order_value_minor * reward.fulfillment_cost_bps, 10000
        )
    elif isinstance(reward, PerPurchaseReward):
        face_per_order = Fraction(reward.rewards_per_purchase) * reward.reward_value_minor
        cost_per_order = Fraction(reward.rewards_per_purchase) * reward.fulfillment_cost_minor
    else:
        face_per_order = cost_per_order = Fraction(0)
        fixed_face = Fraction(reward.issued_rewards * reward.reward_value_minor)
        fixed_cost = Fraction(reward.issued_rewards * reward.fulfillment_cost_minor)
    operating = Fraction(scenario.operating_cost_minor)

    def project(redemption_bps, lift_bps):
        probability = Fraction(redemption_bps, 10000)
        lift = Fraction(lift_bps, 10000)
        projected_orders = orders * (1 + lift)
        projected_sales = sales * (1 + lift)
        face = fixed_face + face_per_order * projected_orders
        cost = probability * (fixed_cost + cost_per_order * projected_orders)
        incremental = sales * lift * margin
        profit = incremental - cost - operating
        baseline_cost = probability * (fixed_cost + cost_per_order * orders)
        variable_rate = (
            probability * cost_per_order / scenario.average_order_value_minor
            if scenario.average_order_value_minor
            else Fraction(0)
        )
        effective = margin - variable_rate
        warnings = ["behavioral_lift_is_assumed"]
        if not sales:
            warnings.append("zero_baseline_sales")
        if margin <= 0:
            warnings.append("nonpositive_contribution_margin")
        if effective <= 0:
            warnings.append("nonpositive_incremental_margin_after_variable_rewards")
        if not projected_sales:
            warnings.append("reward_cost_sales_percentage_undefined")
        if face and not (fixed_cost or cost_per_order):
            warnings.append("positive_reward_value_with_zero_cost_assumption")
        if isinstance(contribution, OrderContributions):
            warnings.append("supplied_order_margin_extrapolated_not_causal")
        if baseline_cost + operating == 0:
            status, needed, required = "covered_at_zero_lift", Fraction(0), Fraction(0)
        elif not sales:
            status, needed, required = "zero_baseline", None, None
        elif effective <= 0:
            status, needed, required = "no_finite_break_even", None, None
        else:
            status = "finite"
            needed = (baseline_cost + operating) / effective
            required = needed / sales * 100
        return Projection(
            assumed_purchase_lift_bps=lift_bps,
            expected_redemption_bps=redemption_bps,
            expected_orders=rounded(projected_orders, 6),
            projected_sales_minor=rounded(projected_sales),
            expected_issued_face_value_minor=rounded(face),
            expected_redeemed_face_value_minor=rounded(face * probability),
            expected_reward_cost_minor=rounded(cost),
            reward_cost_percent_of_sales=(
                rounded(cost / projected_sales * 100, 6) if projected_sales else None
            ),
            incremental_contribution_before_costs_minor=rounded(incremental),
            estimated_incremental_contribution_profit_minor=rounded(profit),
            profitable_under_assumptions=profit > 0,
            break_even=BreakEven(
                status=status,
                incremental_sales_minor=rounded(needed, ceiling=True)
                if needed is not None
                else None,
                required_lift_percent=rounded(required, 6, ceiling=True)
                if required is not None
                else None,
                effective_incremental_margin_percent=rounded(effective * 100, 6),
            ),
            warnings=warnings,
        )

    return SimulationResult(
        scenario_digest=digest(canonical(scenario)),
        scenario=scenario,
        baseline_orders=rounded(orders, 6),
        baseline_sales_minor=rounded(sales),
        baseline_contribution_minor=rounded(sales * margin),
        contribution_margin_percent=rounded(margin * 100, 6),
        projection=project(scenario.expected_redemption_bps, scenario.assumed_purchase_lift_bps),
        sensitivity=[
            project(p, lift)
            for p in scenario.sensitivity.redemption_bps
            for lift in scenario.sensitivity.lift_bps
        ],
        assumptions=[
            "All inputs describe the same declared horizon and currency; no automatic "
            "annualization.",
            "AOV is net of tax, returns and existing benefits, before incremental rewards.",
            "Lift changes purchase frequency only; AOV, customer count and marginal "
            "contribution rate stay constant.",
            "Contribution is before these incremental reward and operating costs; "
            "subtract each cost once.",
            "Fulfillment cost includes the full economic cost of a redeemed reward; "
            "discounts/credits normally cost their face value.",
            "Expected costs apply to all qualifying purchases, including purchases that "
            "would happen anyway.",
            "Only fixed_issuance holds reward count constant as sales change; variable "
            "models scale issuance with orders.",
            "Redemption is an eventual probability for issued rewards; expected cost is "
            "not cash timing or booked liability.",
            "Inputs are hypothetical or caller-supplied; no experiment outcomes, customer "
            "identity or program eligibility were inferred.",
            "No budget caps, purchase-level floors, tax effects, cannibalization, "
            "liability discounting or automatic winner selection are modeled.",
            "Aggregates round once at output; the break-even threshold rounds upward and "
            "profitability uses unrounded values.",
        ],
    )
