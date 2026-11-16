"""Actual workspace, local presentation choices, retained business data/navigation."""

# ruff: noqa: F811 -- pytest fixtures are injected by name
import pytest

from test_browser_security import browser, playwright  # noqa: F401
from test_combined_workspace_browser import site  # noqa: F401


def login(page):
    page.get_by_label("Usuario", exact=True).fill("101")
    page.get_by_label("Contraseña", exact=True).fill("101")
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_label("Vista de color", exact=True).wait_for()


def test_palette_preserves_customer_state_and_survives_navigation(site):
    page, *_ = site
    page.route("**/api/browser-policy", lambda r: r.fulfill(json={"demo_mode": True, "internal_tools": True}))
    page.goto("/workspace/customers?pairing=gray-white")
    login(page)
    search = page.get_by_label("Buscar clientes")
    search.fill("Mateo")
    playwright.expect(page.locator("tbody tr")).to_have_count(4)
    rows = page.locator("tbody").inner_text()
    mutations = []
    page.on(
        "request",
        lambda r: mutations.append(r.url) if r.method not in ("GET", "HEAD") else None,
    )
    for pair in ("cobalt", "forest", "lime", "ink", "violet", "gray-white"):
        page.get_by_label("Vista de color", exact=True).select_option(pair)
        playwright.expect(page.locator("html")).to_have_attribute(
            "data-workspace-pairing", pair
        )
        assert page.locator("tbody").inner_text() == rows
        assert search.input_value() == "Mateo"
    assert mutations == []
    page.locator(".customer-link").filter(has_text="Mateo Restrepo").first.click()
    page.locator(".detail h2").wait_for()
    page.go_back()
    playwright.expect(page.locator("tbody tr")).to_have_count(4)
    page.get_by_role("link", name="Campañas", exact=True).click()
    playwright.expect(page.locator(".campaign-row")).to_have_count(3)
    assert "pairing=gray-white" in page.url
    page.reload()
    playwright.expect(page.get_by_label("Vista de color", exact=True)).to_have_value(
        "gray-white"
    )
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.get_by_label("Vista de color", exact=True).select_option("original")
    assert page.locator("html").get_attribute("data-workspace-pairing") is None


@pytest.mark.parametrize("demo", [True, False])
def test_internal_tools_absent_from_merchant_and_demo(site, demo):
    page, *_ = site
    page.route(
        "**/api/browser-policy", lambda route: route.fulfill(json={"demo_mode": demo, "internal_tools": False})
    )
    page.add_init_script("localStorage.setItem('101.workspace.color-preview', 'lime')")
    page.goto("/workspace/customers?pairing=lime")
    page.get_by_label("Usuario", exact=True).fill("101")
    page.get_by_label("Contraseña", exact=True).fill("101")
    page.get_by_role("button", name="Entrar", exact=True).click()
    playwright.expect(page.locator("tbody tr")).to_have_count(25)
    assert page.get_by_label("Vista de color", exact=True).count() == 0
    assert page.locator("html").get_attribute("data-workspace-pairing") is None

    assert page.get_by_role("link", name="Identidad", exact=True).count() == 0
    assert page.locator(".demo-badge").count() == int(demo)
    page.get_by_role("button", name="Compartir QR").click()
    playwright.expect(page.get_by_role("dialog")).to_be_visible()
