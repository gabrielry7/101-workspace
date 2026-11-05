"""Shared workspace: real HTTP, canonical checkout, mock isolation and visual consumers."""

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import pytest
from sqlalchemy import select
import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright  # noqa: F401
from world_model.restaurant_commerce.workspace_demo import app_for_demo
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER
from world_model.restaurant_commerce.models import Customer, Order, Payment
from world_model.restaurant_commerce.campaign_models import CampaignJob
from world_model.restaurant_commerce.security import sign_webhook

OUT = Path(
    os.environ.get("WORKSPACE_BROWSER_EVIDENCE", "/tmp/101-home-evidence/browser")
)


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    monkeypatch.setattr(
        customers, "app_for_demo", lambda db, url, _count: app_for_demo(db, url)
    )
    OUT.mkdir(parents=True, exist_ok=True)
    yield from customers.site.__wrapped__(tmp_path, browser)


def metric(page, label):
    return (
        page.locator(".report-grid > div")
        .filter(has=page.get_by_text(label, exact=True))
        .locator("strong")
    )


def capture(page, name):
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(OUT / (name + ".png")), full_page=True)


def test_campaign_checkout_unsubscribe_revision_and_refund(site):
    page, context, url, app, *_ = site
    customers.login(page)
    page.get_by_role("link", name="Campañas", exact=True).click()
    playwright.expect(page.locator(".campaign-row")).to_have_count(3)
    page.get_by_role("button", name="Crear campaña", exact=True).click()
    page.get_by_label("Asunto", exact=True).fill("Prueba compartida")
    page.get_by_label("Título del mensaje").fill("Nos vemos en la mesa")
    page.get_by_label("Mensaje", exact=True).fill(
        "Mensaje ficticio escrito por una persona para verificar el flujo completo."
    )
    page.get_by_label("Condiciones y vigencia").fill(
        "Prueba ficticia, sin oferta real."
    )
    for email in [
        "persona0@example.test",
        "persona1@example.test",
        "persona2@example.test",
    ]:
        page.locator(".audience-picker label").filter(has_text=email).get_by_role(
            "checkbox"
        ).check()
    capture(page, "campaign-editor-desktop")
    page.get_by_role("button", name="Guardar y revisar").click()
    playwright.expect(page.locator(".review-summary")).to_be_visible()
    page.frame_locator(".email-preview iframe").get_by_role(
        "heading", name="Nos vemos en la mesa"
    ).wait_for()
    cid = parse_qs(urlsplit(page.url).query)["campaign"][0]
    root = f"/api/operator/restaurants/{BUSINESS}/campaigns/{cid}"
    first = context.request.get(root).json()
    assert first["eligible"] == 2 and first["excluded"] == 1
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Aprobar simulación").click()
    playwright.expect(
        page.get_by_role("button", name="Programar", exact=True)
    ).to_be_enabled()
    page.get_by_role("button", name="Editar", exact=True).click()
    page.get_by_label("Condiciones y vigencia").fill(
        "Condiciones corregidas. Sigue siendo ficticio."
    )
    page.get_by_role("button", name="Guardar y revisar").click()
    playwright.expect(
        page.get_by_role("button", name="Aprobar simulación")
    ).to_be_disabled()
    edited = context.request.get(root).json()
    assert edited["digest"] != first["digest"] and not edited["approved"]
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Aprobar simulación").click()
    page.get_by_role("button", name="Programar", exact=True).click()
    playwright.expect(page.locator(".view-heading p")).to_contain_text("Programada")
    with app.state.session_factory() as s:
        customer = s.scalar(
            select(Customer).where(
                Customer.business_id == BUSINESS,
                Customer.email == "persona1@example.test",
            )
        )
        pending = s.scalar(
            select(CampaignJob).where(
                CampaignJob.customer_id == customer.id,
                CampaignJob.revision_id == edited["revision_id"],
            )
        )
        assert (
            context.request.post(
                "/campaign-unsubscribe/" + pending.unsubscribe_token
            ).status
            == 200
        )
        old_ids = set(s.scalars(select(Order.id)))
    page.get_by_role("button", name="Procesar pendientes del negocio").click()
    playwright.expect(metric(page, "Aceptados por simulador")).to_have_text("1")
    page.get_by_role("button", name="Simular recibos de entrega").click()
    playwright.expect(metric(page, "Entrega reportada")).to_have_text("1")
    page.get_by_text("Ver entregas y enlaces", exact=True).click()
    playwright.expect(page.locator(".delivery-details")).to_contain_text(
        "Baja confirmada"
    )
    capture(page, "campaign-delivery-desktop")
    report = context.request.get(root + "/report?scope=test").json()
    link = next(
        j["tracking_url"] for j in report["deliveries"] if j["state"] == "delivered"
    )
    page.goto(link)
    page.locator("#menu article").filter(has_text="Producto de prueba").get_by_role(
        "button"
    ).click()
    page.locator("#cName").fill("Cliente ficticio")
    page.locator("#cPhone").fill("3005550100")
    page.locator("#checkoutButton").click()
    playwright.expect(page.locator("#checkoutRecovery")).to_contain_text(
        "Pago confirmado"
    )
    capture(page, "checkout-paid")
    with app.state.session_factory() as s:
        order = s.scalar(
            select(Order).where(Order.business_id == BUSINESS, Order.id.notin_(old_ids))
        )
        payment = s.scalar(select(Payment).where(Payment.order_id == order.id))
        assert order.total_minor == 24900 and order.payment_status == "paid"
        body = json.dumps(
            {
                "event_id": "workspace-refund",
                "provider_reference": payment.provider_reference,
                "status": "partially_refunded",
                "amount_minor": 24900,
                "currency": "COP",
                "refund_reference": "workspace-refund-ref",
                "refund_amount_minor": 5000,
            }
        ).encode()
    for _ in range(2):
        assert (
            context.request.post(
                "/api/webhooks/payments/simulated",
                data=body,
                headers={
                    "X-101-Webhook-Signature": sign_webhook(
                        "synthetic-campaign-payment-secret", body
                    ),
                    "Content-Type": "application/json",
                },
            ).status
            == 200
        )
    page.goto("/workspace/campaigns?campaign=" + cid)
    playwright.expect(metric(page, "Pedidos pagados")).to_have_text("1")
    playwright.expect(metric(page, "Capturado menos devuelto")).to_have_text(
        re.compile(r"\$\s*19\.900")
    )
    final = context.request.get(root + "/report?scope=test").json()
    assert (
        final["paid_orders"],
        final["captured_revenue"],
        final["refunds"],
        final["net_revenue"],
    ) == (1, 24900, 5000, 19900)
    assert context.request.get(root + "/report?scope=live").json()["paid_orders"] == 0
    assert context.request.get(root.replace(BUSINESS, OTHER)).status == 403
    capture(page, "campaign-report-desktop")
    page.set_viewport_size({"width": 390, "height": 844})
    capture(page, "campaign-report-mobile")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert (
        page.frame_locator(".email-preview iframe")
        .locator("body")
        .evaluate("(e)=>e.scrollWidth<=innerWidth")
    )
    page.get_by_role("button", name="Cancelar campaña", exact=True).click()
    page.get_by_role("button", name="Sí, cancelar campaña", exact=True).click()
    playwright.expect(page.locator(".view-heading p")).to_contain_text("Cancelada")
    assert context.request.get(root + "/report?scope=test").json()["paid_orders"] == 1
    (OUT / "journey.json").write_text(
        json.dumps(
            {
                "paid_orders": 1,
                "captured_COP": 24900,
                "refund_COP": 5000,
                "net_COP": 19900,
                "real_provider_calls": 0,
                "unsubscribe_prevented_pending_send": True,
                "edit_invalidated_approval": True,
                "duplicate_refund_stable": True,
            },
            indent=2,
        )
    )


def test_period_navigation_mock_isolation_and_business_switch(site):
    page, context, _, _, *_ = site
    customers.login(page, "multi.owner")
    page.get_by_role("link", name="Inicio", exact=True).click()
    page.get_by_label("Desde", exact=True).fill("2026-11-03")
    page.get_by_label("Hasta", exact=True).fill("2026-11-03")
    page.get_by_role("button", name="Aplicar", exact=True).click()
    playwright.expect(
        page.locator(".result-strip > a").first.locator("strong")
    ).to_have_text("31")
    assert page.locator("main h1").count() == 1
    page.get_by_role("link", name=re.compile("Clientes añadidos")).click()
    playwright.expect(page.locator(".customer-link")).to_have_count(4)
    assert "date_from=2026-11-03" in page.url
    page.go_back()
    page.locator(".attention-row").first.click()
    playwright.expect(page.locator(".sale-detail")).to_be_visible()
    assert "date_from=2026-11-03" in page.url
    page.get_by_role("link", name="Analítica web", exact=True).click()
    playwright.expect(page.locator(".demo-notice")).to_contain_text("Datos de ejemplo")
    assert "date_from=2026-11-03" in page.url
    root = f"/api/operator/restaurants/{BUSINESS}/workspace/overview?date_from=2026-11-03&date_to=2026-11-03"
    before = context.request.get(root).json()
    old = page.locator(".analytics-metrics strong").first.inner_text()
    page.get_by_label("Desde", exact=True).fill("2026-10-20")
    page.get_by_role("button", name="Aplicar", exact=True).click()
    playwright.expect(page.locator(".analytics-metrics strong").first).not_to_have_text(
        old
    )
    page.get_by_role("button", name=re.compile("Páginas vistas")).click()
    playwright.expect(
        page.get_by_role("heading", name="Páginas vistas por día")
    ).to_be_visible()
    page.get_by_text("Ver datos diarios", exact=True).click()
    playwright.expect(page.locator(".chart-data tbody tr")).to_have_count(15)
    assert context.request.get(root).json() == before
    page.goto("/workspace/analytics?date_from=bad&date_to=bad")
    playwright.expect(page.get_by_role("alert")).to_contain_text("Elige un periodo")
    page.goto("/workspace/campaigns")
    playwright.expect(page.locator(".campaign-row")).to_have_count(3)
    page.locator(".campaign-row").first.click()
    page.locator("#business").select_option(OTHER)
    playwright.expect(
        page.get_by_role("heading", name="Todavía no hay campañas aquí")
    ).to_be_visible()
    assert page.locator(".review-summary").count() == 0


def test_visual_readability_identity_consumption_and_readonly(site):
    page, context, _, _, *_ = site
    customers.login(page, "sales.viewer")
    axe = (
        Path(__file__).resolve().parents[1]
        / "frontend/node_modules/axe-core/axe.min.js"
    ).read_text()
    violations = {}
    measurements = {}
    for area in ["home", "campaigns", "analytics", "identity"]:
        page.goto("/workspace/" + area)
        page.locator(".view-heading h1").wait_for()
        if area == "home":
            page.locator(".attention-row").first.wait_for()
        if area == "campaigns":
            page.locator(".campaign-row").first.wait_for()
            playwright.expect(
                page.get_by_role("button", name="Crear campaña")
            ).to_be_disabled()
        for width in [1440, 390, 320]:
            page.set_viewport_size(
                {"width": width, "height": 1000 if width > 700 else 844}
            )
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            capture(page, f"{area}-{width}")
            page.evaluate(axe)
            violations[f"{area}-{width}"] = page.evaluate(
                "async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))"
            )
        measurements[area] = page.locator(".view-heading h1").evaluate(
            "(e)=>({font:getComputedStyle(e).fontSize,color:getComputedStyle(e).color})"
        )
    page.goto("/workspace/analytics")
    page.locator(".analytics-metrics").wait_for()
    before = page.locator(".analytics-metrics").inner_text()
    page.evaluate(
        "document.documentElement.style.setProperty('--wm-accent','#183c2d');document.documentElement.style.setProperty('--wm-radius','4px')"
    )
    assert (
        page.locator(".analytics-metrics .selected strong").evaluate(
            "(e)=>getComputedStyle(e).color"
        )
        == "rgb(24, 60, 45)"
    )
    assert (
        page.locator(".chart-panel").evaluate("(e)=>getComputedStyle(e).borderRadius")
        == "4px"
    )
    assert page.locator(".analytics-metrics").inner_text() == before
    capture(page, "identity-token-consumption")
    page.goto("/workspace/campaigns")
    page.locator(".campaign-row").first.click()
    playwright.expect(page.locator(".review-summary")).to_contain_text(
        "Tu acceso permite consultar"
    )
    assert page.get_by_role("button", name="Editar", exact=True).count() == 0
    (OUT / "axe.json").write_text(json.dumps(violations, indent=2))
    (OUT / "measurements.json").write_text(json.dumps(measurements, indent=2))
    assert not any(violations.values()), violations
