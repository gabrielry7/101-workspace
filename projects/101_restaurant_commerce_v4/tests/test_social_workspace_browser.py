"""One normal workspace session across social, customers, sales and campaigns."""
# ruff: noqa: F811 -- imported pytest fixtures are injected by name

import os
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from test_browser_security import browser, playwright  # noqa: F401
from test_combined_workspace_browser import site  # noqa: F401
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD


def open_social(page):
    presence = page.locator(".sidebar details.presence")
    if not presence.evaluate("element => element.open"):
        presence.locator("summary").click()
    page.get_by_role("link", name="Instagram", exact=True).click()


def test_social_roundtrip_in_combined_dashboard(site, tmp_path):
    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    photo = tmp_path / "synthetic.jpg"
    Image.new("RGB", (1200, 1500), "#9b8876").save(photo)
    page.goto("/workspace/home?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.locator(".attention-row").first.wait_for()
    page.screenshot(path=str(evidence / "shared-home-before.png"), full_page=True)
    open_social(page)
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_label("¿Qué quieres conseguir?").fill("Explicar una imagen de prueba")
    page.get_by_label("¿Qué pregunta debe responder?").fill("¿Qué muestra esta imagen?")
    page.get_by_label("Texto que puedes confirmar").fill(
        "Imagen sintética para verificar el espacio compartido."
    )
    page.get_by_label("Revisar estos datos").fill((date.today() + timedelta(days=7)).isoformat())
    page.get_by_label("¿Cómo debe verse y sonar?").fill("Fotografía protagonista, texto claro.")
    page.get_by_label("Permiso para usar").fill("Imagen sintética creada para esta prueba.")
    page.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Preparar publicación", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    # Existing modules retain the session and business selected by the shared shell.
    for name, selector in [
        ("Clientes", ".customer-link"),
        ("Ventas", ".sale-link"),
        ("Campañas", ".campaign-row"),
    ]:
        page.get_by_role("link", name=name, exact=True).click()
        page.locator(selector).first.wait_for()
        assert page.get_by_label("Contraseña", exact=True).count() == 0
        assert BUSINESS in page.url
    open_social(page)
    select = page.get_by_label("Trabajo guardado")
    select.locator("option").nth(1).wait_for(state="attached")
    selected = select.locator("option").nth(1).get_attribute("value")
    select.select_option(selected)
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    download.value.save_as(str(evidence / "shared-package.zip"))
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(evidence / "social-desktop.png"), full_page=True)
    # Cross-business form/library/approval state must be discarded, even for a multi-owner.
    page.locator(".sidebar select").select_option(OTHER)
    page.get_by_role("heading", name="Tu publicación aparecerá aquí").wait_for()
    assert page.get_by_label("Texto que puedes confirmar").input_value() == ""
    assert page.get_by_label("O usa una fotografía guardada").locator("option").count() == 1
    assert page.get_by_label("¿Qué quieres conseguir?").input_value() == ""
    assert page.get_by_role("link", name="Descargar foto", exact=False).count() == 0
    page.locator(".sidebar select").select_option(BUSINESS)
    page.get_by_label("Trabajo guardado").select_option(selected)
    page.get_by_role("button", name="Versión aprobada").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(evidence / "social-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_owner_corrects_shared_price_and_recovers_draft(site, tmp_path):
    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_label("¿Qué quieres ofrecer?", exact=True).fill("Producto de prueba")
    page.get_by_label("Objetivo del negocio", exact=True).fill("Explicar el precio")
    page.get_by_label("¿Cómo pueden comprar o pedir?", exact=True).fill("Consultar en el local")
    page.get_by_role("button", name="Añadir dato", exact=True).click()
    field = page.locator(".social-fact").first
    field.get_by_label("Nombre del dato", exact=True).fill("Precio")
    field.get_by_label("Tipo", exact=True).select_option("money")
    field.get_by_label("Valor", exact=True).fill("12000")
    field.get_by_label("Moneda", exact=True).fill("COP")
    field.get_by_label("Revisar antes de", exact=True).fill(
        (date.today() + timedelta(days=7)).isoformat()
    )
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    page.get_by_role("button", name="Usar objetivo del negocio", exact=True).click()
    page.get_by_label("Precio: 12000 COP.", exact=True).check()
    page.get_by_label("¿Qué pregunta debe responder?", exact=True).fill("¿Cuánto cuesta?")
    page.get_by_label("Revisar estos datos").fill((date.today() + timedelta(days=7)).isoformat())
    page.get_by_label("¿Cómo debe verse y sonar?").fill("Fotografía protagonista.")
    page.get_by_label("Permiso para usar").fill("Imagen sintética creada para la prueba.")
    photo = tmp_path / "fixture.png"
    Image.new("RGB", (1200, 1500), "#998877").save(photo)
    page.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Preparar publicación", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    original = page.locator(".social-image").get_attribute("src")
    page.locator(".social-context summary").click()
    field.get_by_label("Valor", exact=True).fill("15000")
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.locator(".social-stale").wait_for()
    assert page.get_by_role("link", name="Descargar foto", exact=False).count() == 0
    assert page.locator(".social-image").get_attribute("src") == original
    page.screenshot(path=str(evidence / "price-stale-desktop.png"), full_page=True)
    # Reopen stale metadata through ordinary navigation, without database intervention.
    packid = page.get_by_label("Trabajo guardado").input_value()
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.locator(".customer-link").first.wait_for()
    open_social(page)
    page.get_by_label("Trabajo guardado").select_option(packid)
    page.locator(".social-stale").wait_for()
    page.get_by_role("button", name="Revisar con los datos actuales", exact=True).click()
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2").wait_for()
    assert page.locator("aside .social-caption").inner_text() == "Precio: 15000 COP."
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    download.value.save_as(str(evidence / "corrected-price-package.zip"))
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(evidence / "corrected-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator(".social-context summary").click()
    page.screenshot(path=str(evidence / "facts-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    measurements = page.locator(".social-context").evaluate("""e => ({font:getComputedStyle(e).fontFamily,
        inputHeight:e.querySelector('input').getBoundingClientRect().height,
        overflow:document.documentElement.scrollWidth>innerWidth})""")
    import json

    (evidence / "facts-layout.json").write_text(json.dumps(measurements, indent=2))
    assert "Inter" in measurements["font"] and measurements["inputHeight"] >= 44
