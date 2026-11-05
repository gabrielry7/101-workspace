"""Closed, versioned documents shared by configuration and rule previews."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schemas import StrictModel


class Strict(StrictModel):
    pass


Money = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]
Positive = Annotated[int, Field(strict=True, gt=0, le=2**31 - 1)]
Bps = Annotated[int, Field(strict=True, ge=0, le=10000)]


class PointsRule(Strict):
    type: Literal["points"] = "points"
    spend_minor_per_point: Positive
    points_per_unit: Positive = 1


class FixedRule(Strict):
    type: Literal["fixed_value"] = "fixed_value"
    points_cost: Positive
    discount_minor: Positive


class CreditRule(Strict):
    type: Literal["cashback"]
    rate_bps: Bps


class FrequencyRule(Strict):
    type: Literal["frequency"]
    purchases_required: Positive
    reward_value_minor: Money


class MilestoneRule(Strict):
    type: Literal["milestone"]
    spending_threshold_minor: Positive
    reward_value_minor: Money


class TierRule(Strict):
    type: Literal["tier"]
    qualification_days: Positive
    spending_threshold_minor: Positive
    tier_name: str = Field(min_length=1, max_length=100)


class PercentageRule(Strict):
    type: Literal["percentage"]
    points_cost: Positive
    discount_bps: Bps


class ProductRule(Strict):
    type: Literal["product"]
    points_cost: Positive
    product_id: str = Field(min_length=1, max_length=64)
    quantity: Positive = 1


Rule = Annotated[
    PointsRule
    | FixedRule
    | CreditRule
    | FrequencyRule
    | MilestoneRule
    | TierRule
    | PercentageRule
    | ProductRule,
    Field(discriminator="type"),
]


class Eligibility(Strict):
    verified_identity_required: Literal[True] = True
    included_product_ids: list[str] = Field(default_factory=list, max_length=1000)
    excluded_product_ids: list[str] = Field(default_factory=list, max_length=1000)
    customer_ids: list[str] = Field(default_factory=list, max_length=1000)
    minimum_purchase_minor: Money = 0

    @model_validator(mode="after")
    def disjoint(self):
        for values in (self.included_product_ids, self.excluded_product_ids, self.customer_ids):
            if len(values) != len(set(values)) or any(not v.strip() or len(v) > 64 for v in values):
                raise ValueError(
                    "Eligibility IDs must be unique, nonempty and at most 64 characters"
                )
        if set(self.included_product_ids) & set(self.excluded_product_ids):
            raise ValueError("A product cannot be both included and excluded")
        return self


def valid_dates(start, end):
    for value in (start, end):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Dates must include a timezone")
    if start and end and end <= start:
        raise ValueError("End must follow start")


class StrategyDocument(Strict):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    start_at: datetime | None = None
    end_at: datetime | None = None
    eligibility: Eligibility = Field(default_factory=Eligibility)
    earning: PointsRule | None = None
    reward: Rule | None = None
    minimum_redeem_points: Positive = 1
    maximum_reward_minor: Money
    expiration_days: Positive | None = None
    per_customer_budget_minor: Money
    campaign_budget_minor: Money
    estimated_cost_per_point_minor: Money = 0
    expected_redemption_bps: Bps = 10000
    stack_with_promotions: bool = False
    eligible_spend_basis: Literal["net_items_excluding_tax_and_delivery"] = (
        "net_items_excluding_tax_and_delivery"
    )
    rounding: Literal["floor_per_order"] = "floor_per_order"

    @model_validator(mode="after")
    def valid(self):
        valid_dates(self.start_at, self.end_at)
        if self.earning is None and self.reward is None:
            raise ValueError("An earning or reward rule is required")
        if self.per_customer_budget_minor > self.campaign_budget_minor:
            raise ValueError("Customer budget cannot exceed campaign budget")
        return self


class Variant(Strict):
    name: str = Field(min_length=1, max_length=100)
    allocation_bps: Annotated[int, Field(strict=True, gt=0, le=10000)]
    strategy_version_id: str | None = Field(default=None, min_length=1, max_length=36)


class AnalysisProtocol(Strict):
    method: Literal["welch_bonferroni_v1"] = "welch_bonferroni_v1"
    confidence_bps: Literal[9000, 9500, 9900] = 9500
    minimum_customers_per_arm: Annotated[int, Field(strict=True, ge=30, le=10000000)] = 100
    sample_size_rationale: str = Field(min_length=20, max_length=2000)
    readout_at: datetime
    # This threshold is a declared planning choice, not a guarantee of power.


class ExperimentDocument(Strict):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    enrollment_start: datetime
    enrollment_end: datetime
    observation_days: Annotated[int, Field(strict=True, ge=1, le=1095)] = 60
    carryover_days: Annotated[int, Field(strict=True, ge=0, le=1095)] = 0
    eligibility: Eligibility = Field(default_factory=Eligibility)
    variants: list[Variant] = Field(min_length=2, max_length=20)
    exclusion_group: str = Field(min_length=1, max_length=100)
    allow_overlap: bool = False
    overlap_reason: str | None = Field(default=None, max_length=2000)
    baseline_benefits_preserved: Literal[True] = True
    primary_metric: Literal["incremental_contribution_profit_per_randomized_customer"] = (
        "incremental_contribution_profit_per_randomized_customer"
    )
    assignment_algorithm: Literal["sha256-v1"] = "sha256-v1"
    analysis_plan: str = Field(min_length=20, max_length=10000)
    analysis_protocol: AnalysisProtocol | None = None

    @model_validator(mode="after")
    def valid(self):
        valid_dates(self.enrollment_start, self.enrollment_end)
        if sum(v.allocation_bps for v in self.variants) != 10000:
            raise ValueError("Allocations must sum to 10000 basis points")
        if sum(v.strategy_version_id is None for v in self.variants) != 1:
            raise ValueError("Exactly one control must have no incremental incentive")
        if len({v.name for v in self.variants}) != len(self.variants):
            raise ValueError("Variant names must be unique")
        if self.allow_overlap and not (self.overlap_reason or "").strip():
            raise ValueError("Overlap requires an explicit reason")
        if self.analysis_protocol:
            readout = self.analysis_protocol.readout_at
            try:
                earliest_readout = self.enrollment_end + timedelta(days=self.observation_days)
            except OverflowError as exc:
                raise ValueError("Observation window exceeds the supported calendar") from exc
            if readout.utcoffset() is None or readout < earliest_readout:
                raise ValueError("Readout must follow complete enrollment and observation")
        return self


class StrategyCreate(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    document: StrategyDocument


class ExperimentCreate(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    document: ExperimentDocument


class StrategyEdit(Strict):
    expected_revision: Positive
    document: StrategyDocument


class ExperimentEdit(Strict):
    expected_revision: Positive
    document: ExperimentDocument


class Publish(Strict):
    expected_revision: Positive
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class Transition(Strict):
    expected_revision: Positive
    state: Literal["paused", "archived", "active"]
