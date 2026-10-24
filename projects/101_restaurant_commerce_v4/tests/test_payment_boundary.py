import pytest

from world_model.restaurant_commerce.errors import PaymentError
from world_model.restaurant_commerce.payments import SimulatedPaymentProvider, WompiPaymentProvider


def test_simulated_provider_is_offline_and_deterministic():
    provider = SimulatedPaymentProvider()
    checkout = provider.create_checkout(
        order_id="abc",
        public_code="O123",
        amount_minor=25000,
        currency="COP",
        customer_email=None,
    )
    assert checkout.provider_reference == "sim_abc"
    assert checkout.checkout_url == "/demo/pay/sim_abc"


def test_wompi_boundary_fails_closed_when_not_configured():
    with pytest.raises(PaymentError, match="not configured"):
        WompiPaymentProvider(configured=False).create_checkout(
            order_id="abc",
            public_code="O123",
            amount_minor=25000,
            currency="COP",
            customer_email=None,
        )
