"""Passive money projections, tenant/role boundaries and reviewed labels."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from staff_helpers import staff_headers
from test_growth_v2 import pay_and_complete
from test_loyalty_configuration import create, publish
from test_loyalty_execution import (
    configured as configured,  # noqa: PLC0414 - pytest fixture re-export
)
from test_loyalty_execution import (
    factory as factory,  # noqa: PLC0414 - pytest fixture re-export
)
from test_loyalty_execution import fixed_version, refund, service
from test_payment_durability_m3 import request

from world_model.restaurant_commerce.api import create_app
from world_model.restaurant_commerce.errors import (
    ConcurrencyConflictError,
    NotFoundError,
)
from world_model.restaurant_commerce.loyalty_config import LoyaltyConfigurationService
from world_model.restaurant_commerce.loyalty_execution_models import (
    LoyaltyBudget,
    LoyaltyPointLot,
)
from world_model.restaurant_commerce.loyalty_workspace import (
    eligibility_labels,
    overview,
)
from world_model.restaurant_commerce.models import (
    Customer,
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    Order,
    RestaurantCommerceProfile,
    utcnow,
)
from world_model.restaurant_commerce.seed import DEMO_BUSINESS_ID as BID


def counts(session):
    return tuple(
        session.scalar(select(func.count()).select_from(m))
        for m in (LoyaltyAccount, LoyaltyLedgerEntry, Order)
    )


def test_overview_never_creates_accounts_and_degrades_without_optional_history(factory):
    with factory() as s:
        before = counts(s)
        result = overview(s, BID)
        assert result["wallets"]["accounts"] == "0"
        assert result["execution_history_available"] is False
        assert result["legacy_cost_minor"] is None
        assert result["costs"] == result["ledger"] == result["budgets"] == []
        assert result["reads_mutate_wallet"] is False
        assert counts(s) == before
        s.commit()
        assert counts(s) == before


def test_historical_costs_due_expiry_and_campaign_bucket_are_not_double_counted(
    configured, monkeypatch
):
    sessions, vid, cid = configured
    with sessions() as s:
        vid = fixed_version(s, expiration_days=1)
        svc = service(s, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        lot = s.scalar(select(LoyaltyPointLot))
        before = counts(s)
        available = s.scalar(select(LoyaltyAccount.available_points))
        future = utcnow() + timedelta(days=2)
        monkeypatch.setattr(
            "world_model.restaurant_commerce.loyalty_workspace.utcnow", lambda: future
        )
        result = overview(s, BID)
        cost = result["costs"][0]
        assert cost["currency"] == "COP"
        assert (
            int(cost["recorded_cost_minor"])
            == lot.available_points * lot.cost_per_point_minor
        )
        assert cost["recorded_cost_minor"] == cost["due_expiry_cost_minor"]
        assert int(cost["due_expiry_points"]) == lot.available_points > 0
        assert int(result["wallets"]["available_points"]) == available
        assert (
            int(result["wallets"]["unattributed_points"]) == order.total_minor // 1000
        )
        assert result["legacy_cost_minor"] is None
        campaign = s.scalar(select(LoyaltyBudget).where(LoyaltyBudget.scope == "*"))
        assert len(result["budgets"]) == 1
        assert int(result["budgets"][0]["committed_minor"]) == campaign.committed_minor
        assert counts(s) == before
        s.commit()
        assert s.scalar(select(LoyaltyAccount.available_points)) == available


def test_money_precision_and_historical_currency_are_preserved(configured):
    sessions, _, cid = configured
    with sessions() as s:
        profile = s.get(RestaurantCommerceProfile, BID)
        profile.currency = "USD"
        from world_model.restaurant_commerce.models import Menu, MenuCategory, MenuItem

        items = list(
            s.scalars(
                select(MenuItem)
                .join(MenuCategory)
                .join(Menu)
                .where(Menu.business_id == BID)
            )
        )
        for item in items:
            item.currency = "USD"
        s.commit()
        config = LoyaltyConfigurationService(s, "synthetic")
        cost = (2**53 - 1) // 11
        for key in ["usd-one", "usd-two"]:
            vid = publish(
                config,
                create(
                    config,
                    key=key,
                    currency="USD",
                    estimated_cost_per_point_minor=cost,
                    per_customer_budget_minor=2**53 - 1,
                    campaign_budget_minor=2**53 - 1,
                ),
            )["version_id"]
            svc = service(s, vid, cid)
            pay_and_complete(svc, svc.create_order(BID, request(svc)))
        profile.currency = "COP"
        for item in items:
            item.currency = "COP"
        s.commit()
        result = overview(s, BID)
        assert result["currency"] == "COP"
        assert result["costs"][0]["currency"] == "USD"
        assert result["costs"][0]["recorded_cost_minor"] == str(22 * cost)
        assert 22 * cost > 2**53 - 1


def test_refund_holds_match_identity_and_allocation_evidence(configured):
    sessions, vid, cid = configured
    with sessions() as s:
        svc = service(s, vid, cid)
        order = pay_and_complete(svc, svc.create_order(BID, request(svc)))
        refund(svc, order, 1000)
        result = overview(s, BID)
        assert [r["order_id"] for r in result["refund_holds"]["items"]] == [order.id]
        assert result["refund_holds"]["items"][0]["reasons"] == [
            "refund_allocation_required"
        ]
        assert result["refund_holds"]["items"][0]["refund_minor"] == "1000"
        with pytest.raises(NotFoundError):
            overview(s, "not-this-business")


def test_read_permissions_flags_and_eligibility_labels(factory):
    with factory() as s:
        config = LoyaltyConfigurationService(s, "test")
        customer = Customer(business_id=BID, name="Selected person", phone="3005550199")
        s.add(customer)
        s.commit()
        resource = create(config, eligibility={"customer_ids": [customer.id]})
        before = counts(s)
        assert eligibility_labels(s, BID, "programs", resource["id"])["customers"] == [
            "Selected person"
        ]
        with pytest.raises(ConcurrencyConflictError):
            eligibility_labels(
                s, BID, "programs", resource["id"], expected_revision=999
            )
        with pytest.raises(NotFoundError):
            eligibility_labels(s, "foreign", "programs", resource["id"])
        assert counts(s) == before
    app = create_app(
        engine=factory.kw["bind"],
        loyalty_configuration_enabled=True,
        payment_recovery_enabled=False,
    )
    app.state.session_factory = factory
    root = f"/api/operator/restaurants/{BID}/loyalty-config"
    with TestClient(app) as client:
        assert client.get(root + "/overview").status_code in {401, 403}
        staff_headers(client, business_id=BID, role="viewer", name="loyalty.viewer")
        response = client.get(root + "/overview")
        assert response.status_code == 200, response.text
        assert client.get(root.replace(BID, "foreign") + "/overview").status_code == 403
        assert (
            client.get(root + f"/programs/{resource['id']}/eligibility").status_code
            == 200
        )
    disabled = create_app(
        engine=factory.kw["bind"],
        loyalty_configuration_enabled=False,
        payment_recovery_enabled=False,
    )
    with TestClient(disabled) as client:
        staff_headers(client, business_id=BID)
        assert client.get(root + "/overview").status_code == 404


def test_overview_is_consistent_during_concurrent_earning(configured):
    from sqlalchemy import event

    sessions, vid, cid = configured
    fired = False
    engine = sessions.kw["bind"]

    def concurrent_credit(conn, cursor, statement, parameters, context, many):
        nonlocal fired
        if (
            not fired
            and "FROM restaurant_loyalty_accounts" in statement
            and "JOIN" not in statement
        ):
            fired = True
            with sessions() as writer:
                svc = service(writer, vid, cid)
                pay_and_complete(svc, svc.create_order(BID, request(svc)))

    event.listen(engine, "before_cursor_execute", concurrent_credit)
    try:
        with sessions() as reader:
            result = overview(reader, BID)
    finally:
        event.remove(engine, "before_cursor_execute", concurrent_credit)
    assert fired
    available = int(result["wallets"]["available_points"])
    unknown = int(result["wallets"]["unattributed_points"])
    tracked = sum(int(c["tracked_points"]) for c in result["costs"])
    assert (available, unknown, tracked) in [(0, 0, 0), (22, 11, 11)]


def test_historical_notification_review_remains_visible_without_confirmed_refund(
    configured, monkeypatch
):
    from test_loyalty_audit_refunds import (
        test_untraceable_historical_repayment_preserves_notification_for_review as reproduce,
    )

    reproduce(configured, monkeypatch)
    sessions, _, _ = configured
    with sessions() as s:
        result = overview(s, BID)
        assert result["financial_reviews"]["count"] == 1
        assert (
            result["financial_reviews"]["items"][0]["reason"]
            == "invalid_payment_notification"
        )
        assert result["financial_reviews"]["is_confirmed_refund"] is False
        assert result["refund_holds"]["items"] == []
