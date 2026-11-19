"""Built native U07–U09 against real loopback HTTP and guarded fake transports."""

# ruff: noqa: F811 -- pytest fixtures
import json
import os
import re
from datetime import timedelta
from pathlib import Path

import pytest
import test_customer_workspace_browser as customers
from sqlalchemy import func, select
from test_browser_security import browser, playwright  # noqa:F401
from test_growth_channels_workspace import browser_app  # noqa:F401
from test_growth_channels_workspace import (
    forbid_real_provider_network as forbid_real_provider_network,
)
from world_model.restaurant_commerce.campaign_demo import BUSINESS as BID
from world_model.restaurant_commerce.campaign_demo import CLOCK, PASSWORD
from world_model.restaurant_commerce.campaign_models import (
    CampaignJob,
    ContactPermission,
    WhatsAppReply,
)
from world_model.restaurant_commerce.models import OutboundMessage
from world_model.restaurant_commerce.staff import provision

OUT = Path(os.environ.get("CHANNELS_EVIDENCE", "/tmp/101-channels-browser"))
ROOT = f"/api/operator/restaurants/{BID}"


@pytest.fixture
def site(tmp_path, browser, monkeypatch):
    def app(db, url, count):
        value = browser_app(db, url)
        with value.state.session_factory() as s:
            provision(s, "channel.viewer", PASSWORD, BID, "viewer", actor="synthetic-fixture")
        return value

    monkeypatch.setattr(customers, "app_for_demo", app)
    OUT.mkdir(parents=True, exist_ok=True)
    yield from customers.site.__wrapped__(tmp_path, browser)


def signin(page, path, user="campaign.manager"):
    page.goto(path)
    page.get_by_label("Usuario", exact=True).fill(user)
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_url(re.compile(r".*/workspace/(?!login).+"))
    page.evaluate("document.fonts.ready")


def confirm(page):
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Confirmar", exact=True).click()
    playwright.expect(dialog).to_have_count(0)


def capture(page, name):
    result = {}
    for width in [1440, 390, 320]:
        page.set_viewport_size({"width": width, "height": 1000})
        page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
        result[str(width)] = (
            page.evaluate("""() => ({overflow:document.documentElement.scrollWidth-innerWidth,
          font:getComputedStyle(document.body).fontFamily,
          small:[...document.querySelectorAll(
            '.growth-channel-page button,.channel-tabs button,'+
            '.growth-tabs button,.conversation-detail button')]
            .filter(b=>b.getBoundingClientRect().width && b.getBoundingClientRect().height<43)
            .map(b=>b.textContent)})""")
        )
        assert result[str(width)]["overflow"] == 0
        assert "Inter" in result[str(width)]["font"] and not result[str(width)]["small"]
    page.evaluate(
        (
            Path(__file__).resolve().parents[1] / "frontend/node_modules/axe-core/axe.min.js"
        ).read_text()
    )
    result["a11y"] = page.evaluate(
        """async()=> (await axe.run(document.querySelector('main'),{
            runOnly:{type:'tag',values:['wcag2a','wcag2aa']}}))
            .violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))"""
    )
    (OUT / (name + ".json")).write_text(json.dumps(result, indent=2))
    assert not result["a11y"]
    page.set_viewport_size({"width": 1440, "height": 1000})


def review_and_schedule(page):
    page.locator(".review-summary input[type=checkbox]").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    playwright.expect(page.get_by_role("button", name="Programar", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Programar", exact=True).click()
    playwright.expect(
        page.get_by_role("button", name="Cancelar campaña", exact=True)
    ).to_be_enabled()
    playwright.expect(page.locator(".view-heading p")).to_contain_text("Programada")


def test_catalogues_growth_and_manual_plan_handoff(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/customers?business={BID}&view=promotions")
    playwright.expect(page.get_by_role("heading", name="Promociones", exact=True)).to_be_visible()
    playwright.expect(page.get_by_text("SYNTHETIC10", exact=True)).to_be_visible()
    capture(page, "promotions")
    page.get_by_role("button", name="Recompensas", exact=True).click()
    playwright.expect(
        page.get_by_role("heading", name="Recompensa ficticia", exact=True)
    ).to_be_visible()
    capture(page, "rewards")
    page.get_by_role("link", name="Reportes", exact=True).click()
    page.get_by_role("button", name="Comercio y clientes", exact=True).click()
    playwright.expect(
        page.get_by_role("heading", name="Comercio y clientes", exact=True)
    ).to_be_visible()
    capture(page, "growth-report")
    page.goto(f"/workspace/campaigns?business={BID}&view=outbox")
    playwright.expect(
        page.get_by_text("No hay mensajes en esta vista.", exact=True)
    ).to_be_visible()
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(OutboundMessage)) == 0
    page.get_by_role("button", name="Preparar plan de regreso", exact=True).click()
    confirm(page)
    playwright.expect(page.locator(".outbox-message")).to_have_count(7)
    eligible = page.locator(".outbox-message").filter(has_text="+573005550100")
    eligible.get_by_role("button", name="Revisar y preparar mensaje", exact=True).click()
    confirm(page)
    link = page.get_by_role("link", name="Abrir WhatsApp", exact=True)
    playwright.expect(link).to_have_attribute(
        "href", re.compile(r"^https://wa.me/573005550100\?text=")
    )
    with app.state.session_factory() as s:
        rows = list(s.scalars(select(OutboundMessage)))
        assert len(rows) == 7 and all(r.sent_at is None for r in rows)
    capture(page, "manual-handoff")


def test_whatsapp_edit_preserves_template_params_promotion_and_lost_schedule(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/campaigns?business={BID}&campaign=new")
    page.get_by_label("Canal de la campaña", exact=True).select_option("whatsapp")
    select_template = page.get_by_label("Plantilla de WhatsApp", exact=True)
    playwright.expect(select_template.locator("option")).to_have_count(2)
    select_template.select_option(index=1)
    page.get_by_label("Parámetro 1", exact=True).fill("{name}")
    page.get_by_label("Parámetro 2", exact=True).fill("Invitación sintética, sin oferta real.")
    page.get_by_label("Promoción existente", exact=True).select_option("SYNTHETIC10")
    page.locator(".audience-picker label").filter(has_text="Ana ficticia").get_by_role(
        "checkbox"
    ).check()
    capture(page, "whatsapp-editor")
    page.get_by_role("button", name="Guardar y revisar", exact=False).click()
    playwright.expect(page.locator(".email-preview .message-copy")).to_contain_text(
        "Hola Ana ficticia."
    )
    page.locator(".review-summary input[type=checkbox]").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    playwright.expect(page.get_by_role("button", name="Programar", exact=True)).to_be_enabled()
    page.get_by_role("button", name="Editar", exact=True).click()
    playwright.expect(page.get_by_label("Parámetro 2", exact=True)).to_have_value(
        "Invitación sintética, sin oferta real."
    )
    playwright.expect(page.get_by_label("Promoción existente", exact=True)).to_have_value(
        "SYNTHETIC10"
    )
    page.get_by_label("Parámetro 2", exact=True).fill("Texto corregido, solo prueba.")
    page.get_by_role("button", name="Guardar y revisar", exact=False).click()
    playwright.expect(
        page.get_by_role("button", name="Aprobar simulación", exact=True)
    ).to_be_disabled()
    page.locator(".review-summary input[type=checkbox]").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    playwright.expect(page.get_by_role("button", name="Programar", exact=True)).to_be_enabled()
    calls = []

    def lost(route):
        calls.append(route.request.post_data_json)
        assert route.fetch().ok
        route.abort("failed")

    page.route("**/campaigns/*/schedule", lost)
    page.get_by_role("button", name="Programar", exact=True).click()
    page.get_by_role("button", name="Comprobar campaña guardada", exact=True).click()
    playwright.expect(page.locator(".view-heading p")).to_contain_text("Programada")
    assert len(calls) == 1
    page.unroute("**/campaigns/*/schedule", lost)
    page.get_by_role("button", name="Procesar pendientes del negocio", exact=True).click()
    playwright.expect(
        page.get_by_text(
            "Se procesaron los trabajos vencidos del negocio, en simulación.", exact=True
        )
    ).to_be_visible()
    page.get_by_role("button", name="Simular recibos de entrega", exact=True).click()
    playwright.expect(
        page.get_by_text("Recibos simulados registrados.", exact=True)
    ).to_be_visible()
    review = page.locator(".provider-test-review")
    review.locator("summary").click()
    review.get_by_label("Fuente de autorización del destinatario").fill(
        "Synthetic permission explicitly supplied for this fixture"
    )
    review.get_by_label("Límite de costo · USD").fill("1")
    expiry = page.evaluate(
        """iso=>{const d=new Date(iso);
          return new Date(d-d.getTimezoneOffset()*60000).toISOString().slice(0,16)}""",
        (CLOCK + timedelta(hours=2)).isoformat(),
    )
    review.get_by_label("Vence · hora local de este dispositivo").fill(expiry)
    review.get_by_role("checkbox").check()
    review.get_by_role("button", name="Preparar revisión limitada", exact=True).click()
    playwright.expect(page.get_by_text("Envío autorizado: no.", exact=True)).to_be_visible()
    with app.state.session_factory() as s:
        assert list(s.scalars(select(CampaignJob.state))) == ["delivered"]
    capture(page, "whatsapp-review-results")


def test_sms_composition_size_results_and_pause_control(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/campaigns?business={BID}&campaign=new")
    page.get_by_label("Canal de la campaña", exact=True).select_option("sms")
    page.get_by_label("Asunto", exact=True).fill("Prueba SMS nativa")
    page.get_by_label("Título del mensaje", exact=True).fill("Solo prueba")
    page.get_by_label("Mensaje", exact=True).fill("Hola {name}. " + "á" * 80)
    page.get_by_label("Condiciones y vigencia", exact=True).fill("Demostración ficticia.")
    page.locator(".audience-picker label").filter(has_text="Ana ficticia").get_by_role(
        "checkbox"
    ).check()
    page.get_by_role("button", name="Guardar y revisar", exact=False).click()
    playwright.expect(page.locator(".audience-result")).to_contain_text("UCS-2")
    playwright.expect(page.locator(".email-preview .message-copy")).to_contain_text(
        "/campaign-unsubscribe/"
    )
    review_and_schedule(page)
    page.get_by_role("button", name="Procesar pendientes del negocio", exact=True).click()
    playwright.expect(
        page.get_by_text(
            "Se procesaron los trabajos vencidos del negocio, en simulación.", exact=True
        )
    ).to_be_visible()
    page.get_by_role("button", name="Simular recibos de entrega", exact=True).click()
    playwright.expect(
        page.get_by_text("Recibos simulados registrados.", exact=True)
    ).to_be_visible()
    capture(page, "sms-results")
    page.get_by_role("button", name="Campañas", exact=True).first.click()
    tools = page.locator(".campaign-business-tools")
    tools.locator("summary").click()
    tools.get_by_role("button", name="Pausar envíos", exact=True).click()
    tools.get_by_role("button", name="Confirmar cambio de envíos", exact=True).click()
    playwright.expect(
        tools.get_by_role("button", name="Reanudar envíos", exact=True)
    ).to_be_visible()
    capture(page, "campaign-pause")


def test_native_sender_template_configuration_and_readonly(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/connections?business={BID}&provider=whatsapp")
    original_phone = context.request.get(ROOT + "/whatsapp").json()["sender"]["phone_id"]
    form = page.get_by_role("form", name="Configuración del remitente", exact=True)
    form.get_by_label("Fuente de la información", exact=True).fill("Synthetic native source update")
    form.get_by_role("button", name="Guardar remitente", exact=True).click()
    playwright.expect(page.get_by_text("Remitente guardado.", exact=False)).to_be_visible()
    page.get_by_text("Editar plantilla de simulación", exact=True).first.click()
    template = page.get_by_role("form", name=re.compile("^Editar plantilla ")).first
    template.get_by_label("Fuente", exact=True).fill("Synthetic native template source")
    template.get_by_role("button", name="Guardar plantilla de simulación", exact=True).click()
    playwright.expect(
        page.get_by_text("Synthetic native template source", exact=False)
    ).to_be_visible()
    page.get_by_text("Añadir plantilla de simulación", exact=True).click()
    create = page.get_by_role("form", name="Nueva plantilla de simulación", exact=True)
    for label, value in [
        ("Identificador de la plantilla", "888888888"),
        ("Nombre de la plantilla", "native_fixture"),
        ("Idioma", "es_CO"),
        ("Fuente", "Synthetic native new template"),
        ("Texto de la plantilla", "Información sintética."),
        ("Pie de la plantilla", "Responde BAJA."),
    ]:
        create.get_by_label(label, exact=True).fill(value)
    expiry = page.evaluate(
        """iso=>{const d=new Date(iso);
      return new Date(d-d.getTimezoneOffset()*60000).toISOString().slice(0,16)}""",
        (CLOCK + timedelta(days=3)).isoformat(),
    )
    create.get_by_label("Vigencia · hora local de este dispositivo", exact=True).fill(expiry)
    create.get_by_role("button", name="Guardar plantilla de simulación", exact=True).click()
    playwright.expect(page.get_by_text("native_fixture · es_CO", exact=True)).to_be_visible()
    capture(page, "whatsapp-config")
    page.get_by_role("button", name="SMS", exact=True).click()
    form = page.get_by_role("form", name="Configuración del remitente", exact=True)
    form.get_by_label("Precio por mensaje · USD (vacío: desconocido)", exact=True).fill("")
    form.get_by_role("button", name="Guardar remitente", exact=True).click()
    playwright.expect(page.get_by_text("Remitente guardado.", exact=False)).to_be_visible()
    assert context.request.get(ROOT + "/sms").json()["sender"]["unit_cost_microusd"] is None
    capture(page, "sms-config")
    page.go_back()
    playwright.expect(form.get_by_label("Identificador del número", exact=True)).to_have_value(
        original_phone
    )
    context.request.post(
        "/api/staff/logout",
        headers={"X-101-CSRF": context.request.get("/api/staff/me").json()["csrf"]},
    )
    signin(page, f"/workspace/connections?business={BID}&provider=sms", "channel.viewer")
    playwright.expect(
        page.get_by_role("form", name="Configuración del remitente").get_by_label(
            "Número o código remitente"
        )
    ).to_be_disabled()
    assert page.get_by_role("button", name="Guardar remitente", exact=True).count() == 0


def test_inbox_reply_simulation_stop_and_sms_help(site):
    page, context, url, app, *_ = site
    signin(page, f"/workspace/campaigns?business={BID}&view=inbox")
    simulation = page.locator(".inbox-simulation")
    simulation.locator("summary").click()
    simulation.get_by_label("Contacto de prueba", exact=True).select_option(label="Ana ficticia")
    simulation.get_by_label("Mensaje entrante de prueba", exact=True).fill(
        "¿Cómo puedo pedir? Solo prueba."
    )
    simulation.get_by_role("button", name="Registrar mensaje de prueba", exact=True).click()
    confirm(page)
    page.locator("a.inbox-row").first.click()
    detail = page.get_by_role("complementary", name="Detalle de conversación")
    detail.get_by_label("Respuesta de prueba", exact=True).fill("Respuesta sintética del operador.")
    detail.get_by_role("button", name="Revisar respuesta", exact=True).click()
    confirm(page)
    playwright.expect(detail.get_by_text("Asignada a campaign.manager", exact=True)).to_be_visible()
    playwright.expect(
        detail.get_by_text("Respuesta sintética del operador.", exact=True)
    ).to_be_visible()
    capture(page, "inbox-queued-reply")
    detail.get_by_role("button", name="Cerrar conversación", exact=True).click()
    simulation.get_by_role("button", name="Procesar respuestas de prueba", exact=True).click()
    confirm(page)
    page.locator("a.inbox-row").first.click()
    playwright.expect(detail.get_by_text("Aceptada por simulador", exact=True)).to_be_visible()
    detail.get_by_role("button", name="Cerrar conversación", exact=True).click()
    simulation.get_by_label("Mensaje entrante de prueba", exact=True).fill("BAJA")
    simulation.get_by_role("button", name="Registrar mensaje de prueba", exact=True).click()
    confirm(page)
    page.locator("a.inbox-row").first.click()
    playwright.expect(
        detail.get_by_text("Baja registrada. No se permiten respuestas.", exact=True)
    ).to_be_visible()
    assert detail.get_by_role("button", name="Revisar respuesta", exact=True).count() == 0
    capture(page, "inbox-opted-out")
    detail.get_by_role("button", name="Cerrar conversación", exact=True).click()
    page.get_by_role("button", name="SMS", exact=True).click()
    simulation.locator("summary").click()
    simulation.get_by_label("Contacto de prueba", exact=True).select_option(label="Ana ficticia")
    for text in ["STOP", "HELP"]:
        simulation.get_by_label("Mensaje entrante de prueba", exact=True).fill(text)
        simulation.get_by_role("button", name="Registrar mensaje de prueba", exact=True).click()
        confirm(page)
    playwright.expect(page.locator("article.inbox-row")).to_have_count(2)
    capture(page, "sms-inbound-help")
    with app.state.session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WhatsAppReply)) == 1
        assert s.scalar(select(func.count()).select_from(CampaignJob)) == 0
        assert any(
            p.state == "withdrawn"
            for p in s.scalars(select(ContactPermission).where(ContactPermission.channel == "sms"))
        )
