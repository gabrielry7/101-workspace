"""One session reaches loyalty and the shared campaign checkout journey."""

import pytest
import test_customer_workspace_browser as customers
import test_workspace_views_browser as campaigns
from test_browser_security import browser, playwright  # noqa: F401
from world_model.restaurant_commerce.loyalty_workspace_demo import app_for_demo


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    monkeypatch.setattr(
        customers, "app_for_demo", lambda db, url, _count: app_for_demo(db, url)
    )
    yield from customers.site.__wrapped__(tmp_path, browser)


def test_short_login_and_navigation(site):
    page, *_ = site
    page.goto("/workspace/home")
    page.get_by_label("Usuario", exact=True).fill("101")
    page.get_by_label("Contraseña", exact=True).fill("101")
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.locator(".attention-row").first.wait_for()
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.get_by_role("link", name="Fidelización", exact=False).click()
    page.get_by_role("heading", name="Programas", exact=True).wait_for()
    page.get_by_role(
        "link", name="Puntos para la próxima visita", exact=False
    ).wait_for()
    page.get_by_role("link", name="Calculadora", exact=True).click()
    page.get_by_role("button", name="Calcular escenario", exact=True).click()
    page.get_by_role("heading", name="Resultado bajo estos supuestos").wait_for()
    page.get_by_role("link", name="Campañas", exact=True).click()
    playwright.expect(page.locator(".campaign-row")).to_have_count(3)
    page.get_by_role("link", name="Ventas", exact=True).click()
    page.locator(".sale-link").first.wait_for()


def test_campaign_checkout_in_combined_app(site):
    campaigns.test_campaign_checkout_unsubscribe_revision_and_refund(site)
