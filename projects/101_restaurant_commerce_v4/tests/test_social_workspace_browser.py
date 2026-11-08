"""One normal workspace session across social, customers, sales and campaigns."""
# ruff: noqa: F811 -- imported pytest fixtures are injected by name

import os
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from test_browser_security import browser, playwright  # noqa: F401
from test_combined_workspace_browser import site  # noqa: F401
from world_model.restaurant_commerce.campaign_demo import BUSINESS, OTHER, PASSWORD


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
    page.get_by_role("link", name="Contenido", exact=True).click()
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
    page.get_by_role("link", name="Contenido", exact=True).click()
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
    assert page.get_by_role("link", name="Descargar foto", exact=False).count() == 0
    page.locator(".sidebar select").select_option(BUSINESS)
    page.get_by_label("Trabajo guardado").select_option(selected)
    page.get_by_role("button", name="Versión aprobada").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(evidence / "social-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
