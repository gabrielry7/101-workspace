"""Stage-two invariants: pure arithmetic, pinned previews and no reward side effects."""

import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError as SchemaError
from sqlalchemy import select
from staff_helpers import staff_headers
from test_loyalty_configuration import create, document, publish
from test_payment_durability_m3 import factory as shared_factory
from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.errors import NotFoundError, ValidationError
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_preview import preview_published_rules
from world_model.restaurant_commerce.loyalty_rules import (
    MAX_MONEY,
    MAX_POINTS,
    PreviewScenario,
    allocate_discount,
    evaluate_rules,
)
from world_model.restaurant_commerce.loyalty_schemas import StrategyEdit, Transition
from world_model.restaurant_commerce.models import (
    Base,
    Customer,
    Menu,
    MenuCategory,
    MenuItem,
    RestaurantCommerceProfile,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID

factory = shared_factory
AT = datetime(2026, 11, 4, 12, tzinfo=UTC)


def scenario(amount=10000, **changes):
    return PreviewScenario.model_validate(
        {
            "currency": "COP",
            "at": AT,
            "assume_verified_identity": True,
            "customer_id": "customer",
            "lines": [{"line_id": "a", "product_id": "product", "subtotal_minor": amount}],
            **changes,
        }
    )


def fixed(**changes):
    return document(
        reward={"type": "fixed_value", "points_cost": 50, "discount_minor": 3000}, **changes
    )


@pytest.mark.parametrize(
    ("amount", "points", "remainder"),
    [
        (0, 0, 0),
        (999, 0, 999),
        (1000, 1, 0),
        (1001, 1, 1),
        (15001, 15, 1),
    ],
)
def test_points_floor_once_per_order(amount, points, remainder):
    result = evaluate_rules(document(), scenario(amount))
    assert result.earning.points == points
    assert result.earning.remainder_minor == remainder
    assert result.execution_enabled is False
    assert result.budget_check == "not_performed"


def test_spend_units_and_split_lines_have_identical_earning():
    rules = document(
        earning={"type": "points", "spend_minor_per_point": 1000, "points_per_unit": 3}
    )
    single = evaluate_rules(rules, scenario(1999))
    split = evaluate_rules(
        rules,
        scenario(
            lines=[
                {"line_id": "a", "product_id": "product", "subtotal_minor": 999},
                {"line_id": "b", "product_id": "product", "subtotal_minor": 1000},
            ]
        ),
    )
    assert single.earning.points == split.earning.points == 3
    assert single.earning.remainder_minor == split.earning.remainder_minor == 999


def test_reward_debits_its_price_not_minimum_balance_and_reduces_earning_basis():
    result = evaluate_rules(
        fixed(minimum_redeem_points=100),
        scenario(
            redeem_reward=True,
            assumed_available_points=100,
            tax_minor=1900,
            delivery_fee_minor=7000,
        ),
    )
    assert result.redemption.eligible_by_rules
    assert result.redemption.points_required == 100
    assert result.redemption.points_spent == 50
    assert result.redemption.discount_minor == 3000
    assert result.earning.points == 7
    assert result.order_total_minor_before_reward == 18900
    assert result.order_total_minor_after_reward == 15900
    assert result.lines[0].earning_basis_minor == 7000


@pytest.mark.parametrize(
    ("amount", "limit", "discount", "cap"),
    [
        (10000, 2000, 2000, "maximum_reward_minor"),
        (1000, 10000, 1000, "eligible_item_spend"),
        (10000, 0, 0, "maximum_reward_minor"),
    ],
)
def test_reward_caps_never_discount_tax_or_delivery(amount, limit, discount, cap):
    result = evaluate_rules(
        fixed(maximum_reward_minor=limit),
        scenario(
            amount,
            redeem_reward=True,
            assumed_available_points=50,
            tax_minor=900,
            delivery_fee_minor=4000,
        ),
    )
    assert result.redemption.discount_minor == discount
    assert cap in result.redemption.capped_by
    assert result.order_total_minor_after_reward >= 4900
    assert result.redemption.points_spent == (50 if discount else 0)


def test_eligible_product_net_spend_controls_minimum_and_earning():
    rules = fixed(
        stack_with_promotions=True,
        eligibility={
            "included_product_ids": ["product", "excluded"],
            "excluded_product_ids": [],
            "minimum_purchase_minor": 6000,
        },
    )
    # An unrelated expensive line and delivery cannot satisfy the eligible minimum.
    cart = scenario(
        redeem_reward=True,
        assumed_available_points=50,
        delivery_fee_minor=100000,
        lines=[
            {
                "line_id": "a",
                "product_id": "product",
                "subtotal_minor": 6000,
                "promotion_discount_minor": 1000,
            },
            {"line_id": "b", "product_id": "unrelated", "subtotal_minor": 100000},
        ],
    )
    result = evaluate_rules(rules, cart)
    assert result.eligible_item_spend_minor_before_reward == 5000
    assert result.earning.points == result.redemption.points_spent == 0
    assert result.reasons == ["minimum_purchase_not_met"]
    assert result.lines[1].exclusion_reason == "product_not_included"
    allowed = evaluate_rules(
        fixed(
            stack_with_promotions=True,
            eligibility={"excluded_product_ids": ["unrelated"], "minimum_purchase_minor": 5000},
        ),
        cart,
    )
    assert allowed.earning.points == 2
    assert allowed.redemption.discount_minor == 3000
    assert allowed.lines[1].exclusion_reason == "product_excluded"


def test_promotion_stacking_applies_even_to_excluded_lines():
    cart = scenario(
        lines=[
            {"line_id": "a", "product_id": "product", "subtotal_minor": 10000},
            {
                "line_id": "b",
                "product_id": "excluded",
                "subtotal_minor": 1000,
                "promotion_discount_minor": 1,
            },
        ],
        redeem_reward=True,
        assumed_available_points=50,
    )
    result = evaluate_rules(fixed(eligibility={"excluded_product_ids": ["excluded"]}), cart)
    assert result.reasons == ["promotion_stacking_disallowed"]
    assert result.earning.points == result.redemption.discount_minor == 0


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"currency": "USD"}, "currency_mismatch"),
        ({"assume_verified_identity": False}, "verified_identity_required"),
        ({"lines": []}, "no_eligible_spend"),
    ],
)
def test_common_eligibility_blocks_both_actions(changes, reason):
    result = evaluate_rules(
        fixed(), scenario(redeem_reward=True, assumed_available_points=100, **changes)
    )
    assert reason in result.reasons
    assert result.earning.points == result.redemption.discount_minor == 0


def test_customer_allowlist_and_date_boundaries():
    rules = fixed(
        start_at=AT, end_at=AT + timedelta(days=1), eligibility={"customer_ids": ["customer"]}
    )
    assert evaluate_rules(rules, scenario()).eligible_by_rules
    assert (
        "program_not_started"
        in evaluate_rules(rules, scenario(at=AT - timedelta(microseconds=1))).reasons
    )
    assert "program_ended" in evaluate_rules(rules, scenario(at=AT + timedelta(days=1))).reasons
    assert "customer_not_included" in evaluate_rules(rules, scenario(customer_id="other")).reasons


def test_point_expiration_is_explicit_and_deterministic():
    first = evaluate_rules(document(expiration_days=30), scenario())
    assert first.earning.expires_at == AT + timedelta(days=30)
    assert first == evaluate_rules(document(expiration_days=30), scenario())
    assert evaluate_rules(document(expiration_days=30), scenario(999)).earning.expires_at is None
    with pytest.raises(ValidationError, match="expiration"):
        evaluate_rules(document(expiration_days=2**31 - 1), scenario())


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"assumed_available_points": 49}, "insufficient_points"),
        (
            {"assumed_available_points": 50, "assumed_refund_debt_points": 1},
            "outstanding_refund_debt",
        ),
    ],
)
def test_failed_redemption_preserves_earning_without_crediting_new_points_first(changes, reason):
    result = evaluate_rules(fixed(), scenario(100000, redeem_reward=True, **changes))
    assert reason in result.redemption.reasons
    assert result.redemption.discount_minor == result.redemption.points_spent == 0
    assert result.earning.points == 100


def test_unrequested_redemption_and_unconfigured_actions():
    assert evaluate_rules(fixed(), scenario()).redemption.reasons == ["redemption_not_requested"]
    missing = evaluate_rules(document(), scenario(redeem_reward=True))
    assert missing.redemption.reasons == ["no_redemption_rule"]
    reward_only = evaluate_rules(
        fixed(earning=None), scenario(redeem_reward=True, assumed_available_points=50)
    )
    assert reward_only.redemption.discount_minor == 3000
    assert reward_only.earning.reasons == ["no_earning_rule"]


@pytest.mark.parametrize(
    "reward",
    [
        {"type": "cashback", "rate_bps": 200},
        {"type": "frequency", "purchases_required": 5, "reward_value_minor": 1000},
        {"type": "milestone", "spending_threshold_minor": 1000, "reward_value_minor": 100},
        {
            "type": "tier",
            "qualification_days": 30,
            "spending_threshold_minor": 1000,
            "tier_name": "Gold",
        },
        {"type": "percentage", "points_cost": 10, "discount_bps": 200},
        {"type": "product", "points_cost": 10, "product_id": "product"},
        {"type": "points", "spend_minor_per_point": 100},
    ],
)
def test_unsupported_rules_fail_closed_instead_of_becoming_points(reward):
    result = evaluate_rules(
        document(reward=reward), scenario(redeem_reward=True, assumed_available_points=100)
    )
    assert not result.supported and not result.eligible_by_rules
    assert result.reasons == ["unsupported_reward_type:" + reward["type"]]
    assert result.earning.points == result.redemption.discount_minor == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"lines": [{"line_id": "a", "product_id": "p", "subtotal_minor": -1}]},
        {"lines": [{"line_id": "a", "product_id": "p", "subtotal_minor": 1.5}]},
        {"lines": [{"line_id": "a", "product_id": "p", "subtotal_minor": True}]},
        {
            "lines": [
                {
                    "line_id": "a",
                    "product_id": "p",
                    "subtotal_minor": 10,
                    "promotion_discount_minor": 11,
                }
            ]
        },
        {"lines": [{"line_id": "a", "product_id": "p", "subtotal_minor": 1}] * 2},
        {"at": datetime(2026, 1, 1)},
        {"at": "0001-01-01T00:00:00+14:00"},
        {"at": "9999-12-31T23:59:59-14:00"},
        {"assumed_available_points": -1},
        {"assume_verified_identity": "true"},
        {"customer_id": None},
        {"delivery_fee_minor": MAX_MONEY},
    ],
)
def test_invalid_scenarios_are_rejected(changes):
    with pytest.raises(SchemaError):
        scenario(**changes)


def test_large_exact_currency_and_point_overflow():
    result = evaluate_rules(
        document(earning={"type": "points", "spend_minor_per_point": MAX_POINTS}),
        scenario(MAX_MONEY),
    )
    assert result.earning.points == MAX_MONEY // MAX_POINTS
    assert result.earning.remainder_minor == MAX_MONEY % MAX_POINTS
    with pytest.raises(ValidationError, match="account range"):
        evaluate_rules(
            document(earning={"type": "points", "spend_minor_per_point": 1}), scenario(MAX_MONEY)
        )


@given(
    st.lists(st.integers(min_value=0, max_value=10**10), min_size=1, max_size=20),
    st.integers(min_value=0, max_value=10**10),
)
def test_allocation_conserves_money_and_is_permutation_invariant(values, proposed):
    weights = {str(i): v for i, v in enumerate(values)}
    amount = min(sum(values), proposed)
    allocations = allocate_discount(amount, weights)
    assert sum(allocations.values()) == amount
    assert all(0 <= allocations[k] <= weights[k] for k in weights)
    assert allocations == allocate_discount(amount, dict(reversed(list(weights.items()))))


@given(st.integers(min_value=1, max_value=10**8), st.integers(min_value=1, max_value=10000))
def test_points_are_monotonic_and_split_invariant(amount, unit):
    rules = document(earning={"type": "points", "spend_minor_per_point": unit})
    original = evaluate_rules(rules, scenario(amount))
    increased = evaluate_rules(rules, scenario(amount + 1))
    split = evaluate_rules(
        rules,
        scenario(
            lines=[
                {"line_id": "a", "product_id": "product", "subtotal_minor": amount // 2},
                {"line_id": "b", "product_id": "product", "subtotal_minor": amount - amount // 2},
            ]
        ),
    )
    assert original.earning.points == split.earning.points == amount // unit
    assert increased.earning.points >= original.earning.points


def setup_published(session):
    customer = Customer(business_id=BID, phone="3001013102", name="Preview only")
    session.add(customer)
    session.commit()
    item = session.scalar(
        select(MenuItem).join(MenuCategory).join(Menu).where(Menu.business_id == BID)
    )
    service = LoyaltyConfigurationService(session, "test-manager")
    draft = create(service)
    version = publish(service, draft)
    cart = scenario(
        customer_id=customer.id,
        lines=[{"line_id": "a", "product_id": item.id, "subtotal_minor": 10000}],
    )
    return service, draft, version, cart


def financial_snapshot(session):
    names = [
        "restaurant_loyalty_accounts",
        "restaurant_loyalty_ledger",
        "restaurant_rewards",
        "restaurant_reward_redemptions",
        "restaurant_orders",
        "restaurant_payments",
        "restaurant_loyalty_refund_debts",
        "restaurant_loyalty_configuration_audit",
    ]
    return {
        name: [tuple(r) for r in session.execute(select(Base.metadata.tables[name]))]
        for name in names
    }


def test_version_pinned_preview_survives_edits_and_archive_without_mutation(factory):
    with factory() as session:
        service, draft, version, cart = setup_published(session)
        before = financial_snapshot(session)
        original = preview_published_rules(session, BID, draft["id"], version["version_id"], cart)
        assert original.result.earning.points == 10
        assert financial_snapshot(session) == before
        current = service.get("programs", BID, draft["id"])
        edited = service.edit(
            "programs",
            BID,
            draft["id"],
            StrategyEdit(
                expected_revision=current["revision"],
                document=document(earning={"type": "points", "spend_minor_per_point": 500}),
            ),
        )
        new_version = publish(service, edited)
        current = service.get("programs", BID, draft["id"])
        service.transition(
            "programs",
            BID,
            draft["id"],
            Transition(expected_revision=current["revision"], state="archived"),
        )
        assert (
            preview_published_rules(session, BID, draft["id"], version["version_id"], cart)
            == original
        )
        assert (
            preview_published_rules(
                session, BID, draft["id"], new_version["version_id"], cart
            ).result.earning.points
            == 20
        )
        assert (
            original.scenario_digest
            != preview_published_rules(
                session,
                BID,
                draft["id"],
                version["version_id"],
                cart.model_copy(update={"assumed_available_points": 1}),
            ).scenario_digest
        )


def test_preview_rejects_foreign_resource_version_product_and_customer(factory):
    with factory() as session:
        service, draft, version, cart = setup_published(session)
        for business, program, vid in [
            ("other", draft["id"], version["version_id"]),
            (BID, "wrong", version["version_id"]),
            (BID, draft["id"], draft["id"]),
        ]:
            with pytest.raises(NotFoundError):
                preview_published_rules(session, business, program, vid, cart)
        session.add(
            RestaurantCommerceProfile(business_id="other", slug="other", display_name="Other")
        )
        session.commit()
        foreign_customer = Customer(business_id="other", phone="3000000031", name="Other")
        foreign_menu = Menu(business_id="other", name="Other menu")
        session.add_all([foreign_customer, foreign_menu])
        session.flush()
        category = MenuCategory(menu_id=foreign_menu.id, name="Other category")
        session.add(category)
        session.flush()
        item = MenuItem(category_id=category.id, name="Other item", base_price_minor=100)
        session.add(item)
        session.commit()
        for payload in [
            cart.model_copy(update={"customer_id": foreign_customer.id}),
            scenario(
                lines=[{"line_id": "a", "product_id": item.id, "subtotal_minor": 100}],
                customer_id=cart.customer_id,
            ),
        ]:
            with pytest.raises(ValidationError):
                preview_published_rules(session, BID, draft["id"], version["version_id"], payload)


def test_http_preview_is_scoped_flagged_and_has_no_financial_side_effects(factory):
    with factory() as session:
        _, draft, version, cart = setup_published(session)
        engine = session.get_bind()
        before = financial_snapshot(session)
    route = (
        f"/api/operator/restaurants/{BID}/loyalty-config/programs/{draft['id']}"
        f"/versions/{version['version_id']}/preview"
    )
    body = cart.model_dump(mode="json")
    with TestClient(
        create_app(
            engine=engine, payment_recovery_enabled=False, loyalty_configuration_enabled=False
        )
    ) as client:
        assert client.post(route, json=body).status_code == 404
    with TestClient(
        create_app(
            engine=engine, payment_recovery_enabled=False, loyalty_configuration_enabled=True
        )
    ) as client:
        assert client.post(route, json=body).status_code == 401
        headers = staff_headers(client, role="viewer", name="preview.viewer")
        assert client.post(route, json=body).status_code == 403
        response = client.post(route, json=body, headers=headers)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["version_id"] == version["version_id"]
        assert result["result"]["earning"]["points"] == 10
        assert result["result"]["budget_check"] == "not_performed"
        assert result["result"]["execution_enabled"] is False
        assert result["result"]["mode"] == "hypothetical"
        assert client.post(route, json=body, headers=headers).json() == result
        assert (
            client.post(route.replace(BID, "other"), json=body, headers=headers).status_code == 403
        )
        bad = json.loads(json.dumps(body))
        bad["lines"][0]["subtotal_minor"] = 1.5
        assert client.post(route, json=bad, headers=headers).status_code == 422
        caps = client.get(
            f"/api/operator/restaurants/{BID}/loyalty-config/capabilities", headers=headers
        ).json()
        assert caps["preview_enabled"] and not caps["execution_enabled"]
    with factory() as session:
        assert financial_snapshot(session) == before


def test_expiration_uses_elapsed_utc_days_across_dst_and_json_replay():
    local = datetime(2026, 10, 31, 12, tzinfo=ZoneInfo("America/New_York"))
    cart = scenario(at=local)
    replay = PreviewScenario.model_validate_json(cart.model_dump_json())
    rules = document(expiration_days=2)
    result = evaluate_rules(rules, cart)
    assert result == evaluate_rules(rules, replay)
    assert result.earning.expires_at == local.astimezone(UTC) + timedelta(days=2)
    assert result.at.utcoffset() == timedelta(0)
