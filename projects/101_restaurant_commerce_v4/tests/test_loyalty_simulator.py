"""Worked economics, exact boundaries and the actual scoped staff consumer."""

import json
from decimal import Decimal
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from sqlalchemy import func, select
from staff_helpers import staff_headers
from test_payment_durability_m3 import factory as shared_factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.loyalty_config import canonical, digest
from world_model.restaurant_commerce.loyalty_models import LoyaltyConfigurationAudit
from world_model.restaurant_commerce.loyalty_simulator import SimulationScenario, simulate
from world_model.restaurant_commerce.models import LoyaltyAccount, LoyaltyLedgerEntry, Order
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID

factory = shared_factory


def inputs(**changes):
    return {
        "currency": "COP",
        "horizon_days": 90,
        "average_order_value_minor": 10000,
        "purchases_per_customer": "2",
        "customer_count": 1000,
        "contribution": {"type": "margin", "contribution_margin_bps": 3000},
        "reward": {"type": "proportional", "reward_value_bps": 200, "fulfillment_cost_bps": 200},
        "expected_redemption_bps": 5000,
        "operating_cost_minor": 100000,
        "assumed_purchase_lift_bps": 1000,
        **changes,
    }


def run(**changes):
    return simulate(SimulationScenario.model_validate(inputs(**changes)))


def test_proportional_hand_calculated_economics():
    result = run()
    assert result.baseline_sales_minor == "20000000"
    assert result.baseline_contribution_minor == "6000000"
    p = result.projection
    assert p.expected_orders == "2200.000000"
    assert p.projected_sales_minor == "22000000"
    assert p.expected_issued_face_value_minor == "440000"
    assert p.expected_redeemed_face_value_minor == "220000"
    assert p.expected_reward_cost_minor == "220000"
    assert p.reward_cost_percent_of_sales == "1.000000"
    assert p.incremental_contribution_before_costs_minor == "600000"
    assert p.estimated_incremental_contribution_profit_minor == "280000"
    # At zero lift cost=200000+100000. Each extra minor unit contributes .30-.01.
    assert p.break_even.incremental_sales_minor == "1034483"
    assert p.break_even.required_lift_percent == "5.172414"
    assert p.profitable_under_assumptions
    assert result.lift_is_assumed and not result.causal_effect_estimated


def test_fixed_issuance_does_not_grow_with_lift():
    reward = {
        "type": "fixed_issuance",
        "reward_value_minor": 1000,
        "fulfillment_cost_minor": 600,
        "issued_rewards": 1000,
    }
    low = run(reward=reward, assumed_purchase_lift_bps=0).projection
    high = run(reward=reward).projection
    assert low.expected_reward_cost_minor == high.expected_reward_cost_minor == "300000"
    assert low.estimated_incremental_contribution_profit_minor == "-400000"
    assert high.estimated_incremental_contribution_profit_minor == "200000"
    assert high.break_even.incremental_sales_minor == "1333334"
    assert high.break_even.required_lift_percent == "6.666667"


def test_purchase_frequency_reward_uses_actual_cost_not_face_value():
    p = run(
        reward={
            "type": "per_purchase",
            "reward_value_minor": 1000,
            "fulfillment_cost_minor": 600,
            "rewards_per_purchase": "0.2",
        }
    ).projection
    assert p.expected_issued_face_value_minor == "440000"
    assert p.expected_reward_cost_minor == "132000"
    assert p.estimated_incremental_contribution_profit_minor == "368000"
    assert p.break_even.incremental_sales_minor == "748300"
    assert p.break_even.required_lift_percent == "3.741497"


def test_supplied_order_contribution_is_revenue_weighted_and_labeled():
    result = run(
        contribution={
            "type": "order_contributions",
            "source_reference": "synthetic-cost-sheet-v1",
            "orders": [
                {"revenue_minor": 10000, "contribution_minor": 5000},
                {"revenue_minor": 90000, "contribution_minor": 25000},
            ],
        }
    )
    assert result.contribution_margin_percent == "30.000000"
    assert result.projection.estimated_incremental_contribution_profit_minor == "280000"
    assert "supplied_order_margin_extrapolated_not_causal" in result.projection.warnings
    assert result.causal_effect_estimated is False


@pytest.mark.parametrize("margin", [100, 0, -1000])
def test_zero_or_negative_effective_margin_has_no_finite_break_even(margin):
    p = run(contribution={"type": "margin", "contribution_margin_bps": margin}).projection
    assert p.break_even.status == "no_finite_break_even"
    assert p.break_even.incremental_sales_minor is None
    assert p.break_even.required_lift_percent is None
    assert not p.profitable_under_assumptions


def test_zero_cost_zero_redemption_and_zero_margin_break_even():
    p = run(
        expected_redemption_bps=0,
        operating_cost_minor=0,
        contribution={"type": "margin", "contribution_margin_bps": 0},
    ).projection
    assert p.break_even.status == "covered_at_zero_lift"
    assert p.break_even.incremental_sales_minor == "0"
    assert p.estimated_incremental_contribution_profit_minor == "0"
    assert not p.profitable_under_assumptions  # Exactly zero is not positive profit.


@pytest.mark.parametrize(
    "changes",
    [{"customer_count": 0}, {"average_order_value_minor": 0}, {"purchases_per_customer": "0"}],
)
def test_zero_sales_does_not_invent_lift_or_divide_by_zero(changes):
    p = run(**changes).projection
    assert p.break_even.status == "zero_baseline"
    assert p.break_even.required_lift_percent is None
    assert p.reward_cost_percent_of_sales is None
    assert p.estimated_incremental_contribution_profit_minor == "-100000"


def test_complete_purchase_loss_retains_fixed_cost():
    p = run(
        assumed_purchase_lift_bps=-10000,
        reward={
            "type": "fixed_issuance",
            "issued_rewards": 1000,
            "reward_value_minor": 1000,
            "fulfillment_cost_minor": 600,
        },
    ).projection
    assert p.expected_orders == "0.000000"
    assert p.expected_reward_cost_minor == "300000"
    assert p.estimated_incremental_contribution_profit_minor == "-6400000"
    assert p.reward_cost_percent_of_sales is None


def test_no_lift_full_redemption_and_zero_cost_warning():
    p = run(assumed_purchase_lift_bps=0, expected_redemption_bps=10000).projection
    assert p.estimated_incremental_contribution_profit_minor == "-500000"
    assert not p.profitable_under_assumptions
    p = run(
        reward={"type": "proportional", "reward_value_bps": 200, "fulfillment_cost_bps": 0}
    ).projection
    assert "positive_reward_value_with_zero_cost_assumption" in p.warnings


def test_round_only_at_output_and_keep_large_money_lossless():
    result = run(
        average_order_value_minor=1,
        purchases_per_customer="0.5",
        customer_count=1,
        expected_redemption_bps=10000,
        assumed_purchase_lift_bps=0,
        operating_cost_minor=0,
        reward={
            "type": "per_purchase",
            "reward_value_minor": 1,
            "fulfillment_cost_minor": 1,
            "rewards_per_purchase": "1",
        },
    )
    assert result.projection.expected_reward_cost_minor == "1"  # Half away from zero.
    assert result.projection.estimated_incremental_contribution_profit_minor == "-1"
    result = run(
        average_order_value_minor=2**53 - 1, purchases_per_customer="1000000", customer_count=10**9
    )
    assert result.baseline_sales_minor == str((2**53 - 1) * 10**15)
    payload = json.loads(result.model_dump_json())
    assert isinstance(payload["baseline_sales_minor"], str)
    assert not any(isinstance(v, float) for v in payload["projection"].values())


def test_sensitivity_matches_separate_scenarios_and_preserves_inputs():
    scenario = SimulationScenario.model_validate(inputs())
    before = scenario.model_dump_json()
    result = simulate(scenario)
    assert len(result.sensitivity) == 9
    for cell in result.sensitivity:
        expected = run(
            expected_redemption_bps=cell.expected_redemption_bps,
            assumed_purchase_lift_bps=cell.assumed_purchase_lift_bps,
        ).projection
        assert cell == expected
    assert scenario.model_dump_json() == before
    assert result.scenario_digest == digest(canonical(scenario))
    assert simulate(SimulationScenario.model_validate_json(before)) == result


@pytest.mark.parametrize(
    "changes",
    [
        {"average_order_value_minor": 1.1},
        {"average_order_value_minor": True},
        {"customer_count": True},
        {"purchases_per_customer": 2.5},
        {"purchases_per_customer": True},
        {"purchases_per_customer": "NaN"},
        {"purchases_per_customer": "1e100000000"},
        {"purchases_per_customer": "0.1234567"},
        {"horizon_days": 0},
        {"expected_redemption_bps": 10001},
        {"assumed_purchase_lift_bps": -10001},
        {"sensitivity": {"redemption_bps": [1, 1], "lift_bps": [0]}},
        {"sensitivity": {"redemption_bps": list(range(10)), "lift_bps": [0]}},
        {"sensitivity": {"redemption_bps": [], "lift_bps": [0]}},
        {
            "contribution": {
                "type": "order_contributions",
                "source_reference": "\x00",
                "orders": [{"revenue_minor": 1, "contribution_minor": 0}],
            }
        },
        {
            "contribution": {
                "type": "order_contributions",
                "source_reference": "synthetic",
                "orders": [{"revenue_minor": 0, "contribution_minor": 0}],
            }
        },
        {
            "contribution": {
                "type": "order_contributions",
                "source_reference": "synthetic",
                "orders": [{"revenue_minor": 1, "contribution_minor": 2}],
            }
        },
        {"contribution": {"type": "margin", "contribution_margin_bps": 10001}},
        {"reward": {"type": "machine_learning"}},
        {"winner": True},
    ],
)
def test_strict_bounded_input(changes):
    with pytest.raises(ValidationError):
        SimulationScenario.model_validate(inputs(**changes))


@given(
    margin=st.integers(2, 10000),
    cost=st.integers(1, 10000),
    sales=st.integers(1, 1000000),
    operating=st.integers(0, 10000),
)
def test_break_even_ceiling_is_minimum_minor_unit_covering_cost(margin, cost, sales, operating):
    if margin <= cost:
        return
    p = run(
        average_order_value_minor=sales,
        customer_count=1,
        purchases_per_customer="1",
        contribution={"type": "margin", "contribution_margin_bps": margin},
        reward={"type": "proportional", "reward_value_bps": cost, "fulfillment_cost_bps": cost},
        expected_redemption_bps=10000,
        operating_cost_minor=operating,
    ).projection
    required = int(p.break_even.incremental_sales_minor)

    def profit(extra):
        return Fraction(extra * margin - (sales + extra) * cost, 10000) - operating

    assert profit(required) >= 0
    assert profit(required - 1) < 0
    # Percentage threshold also rounds upward, independently of money display.
    exact = Fraction(sales * cost + operating * 10000, margin - cost) / sales * 100
    assert Fraction(Decimal(p.break_even.required_lift_percent)) >= exact


def table_counts(session):
    return [
        session.scalar(select(func.count()).select_from(model))
        for model in (Order, LoyaltyAccount, LoyaltyLedgerEntry, LoyaltyConfigurationAudit)
    ]


def test_staff_api_scope_flag_no_writes_and_assumptions(factory):
    engine = factory.kw["bind"]
    root = f"/api/operator/restaurants/{BID}/loyalty-config"
    with TestClient(create_app(engine=engine, payment_recovery_enabled=False)) as client:
        assert client.post(root + "/simulator", json=inputs()).status_code == 404
    with TestClient(
        create_app(
            engine=engine, payment_recovery_enabled=False, loyalty_configuration_enabled=True
        )
    ) as client:
        assert client.post(root + "/simulator", json=inputs()).status_code == 401
        viewer = staff_headers(client, role="viewer", name="simulation-viewer")
        assert client.post(root + "/simulator", json=inputs()).status_code == 403
        with factory() as session:
            before = table_counts(session)
        response = client.post(root + "/simulator", json=inputs(), headers=viewer)
        assert response.status_code == 200, response.text
        assert response.json() == run().model_dump(mode="json")
        assert (
            client.post(
                root.replace(BID, "other") + "/simulator", json=inputs(), headers=viewer
            ).status_code
            == 403
        )
        assert (
            client.post(
                root + "/simulator", json=inputs(purchases_per_customer=2.5), headers=viewer
            ).status_code
            == 422
        )
        with factory() as session:
            assert table_counts(session) == before
        capabilities = client.get(root + "/capabilities", headers=viewer).json()
        assert capabilities["simulator_enabled"]
        assert not capabilities["execution_enabled"] and not capabilities["analytics_enabled"]


@given(probability=st.integers(0, 10000), lift=st.integers(-10000, 100000))
def test_equivalent_variable_models_and_redemption_monotonicity(probability, lift):
    proportional = run(
        expected_redemption_bps=probability, assumed_purchase_lift_bps=lift
    ).projection
    per_purchase = run(
        expected_redemption_bps=probability,
        assumed_purchase_lift_bps=lift,
        reward={
            "type": "per_purchase",
            "reward_value_minor": 200,
            "fulfillment_cost_minor": 200,
            "rewards_per_purchase": "1",
        },
    ).projection
    assert proportional == per_purchase
    full = run(expected_redemption_bps=10000, assumed_purchase_lift_bps=lift).projection
    assert int(full.expected_reward_cost_minor) >= int(proportional.expected_reward_cost_minor)
    assert int(full.estimated_incremental_contribution_profit_minor) <= int(
        proportional.estimated_incremental_contribution_profit_minor
    )
