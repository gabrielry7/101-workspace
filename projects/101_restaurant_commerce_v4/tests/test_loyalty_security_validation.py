"""Regression for authenticated loyalty inputs causing PostgreSQL NUL failures."""

import pytest
from pydantic import ValidationError
from world_model.restaurant_commerce.loyalty_rules import PreviewScenario
from world_model.restaurant_commerce.loyalty_schemas import StrategyCreate


@pytest.mark.parametrize("bad", ["bad\x00id", "bad\ud800id"])
@pytest.mark.parametrize("field", ["customer_id", "product_id", "line_id"])
def test_preview_rejects_non_database_unicode_before_queries(bad, field):
    body = {
        "currency": "COP",
        "at": "2026-11-04T12:00:00Z",
        "customer_id": "customer",
        "lines": [{"line_id": "line", "product_id": "product", "subtotal_minor": 1000}],
    }
    if field == "customer_id":
        body[field] = bad
    else:
        body["lines"][0][field] = bad
    with pytest.raises(ValidationError):
        PreviewScenario.model_validate(body)


@pytest.mark.parametrize("bad", ["bad\x00name", "bad\udfffname"])
def test_configuration_uses_same_strict_boundary(bad):
    body = {
        "request_key": "fixture",
        "document": {
            "name": bad,
            "currency": "COP",
            "earning": {"type": "points", "spend_minor_per_point": 1000},
            "maximum_reward_minor": 10000,
            "per_customer_budget_minor": 10000,
            "campaign_budget_minor": 10000,
        },
    }
    with pytest.raises(ValidationError):
        StrategyCreate.model_validate(body)
