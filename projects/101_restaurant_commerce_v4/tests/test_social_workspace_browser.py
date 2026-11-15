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
    page.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    page.locator(".social-context-manual summary").click()
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
    page.locator("#social-production-form").get_by_label("Precio: 12000 COP.", exact=True).check()
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
    page.locator(".business-context > summary").click()
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
    page.locator(".business-context > summary").click()
    page.screenshot(path=str(evidence / "facts-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    measurements = page.locator(".business-context").evaluate("""e => ({font:getComputedStyle(e).fontFamily,
        inputHeight:e.querySelector('input').getBoundingClientRect().height,
        overflow:document.documentElement.scrollWidth>innerWidth})""")
    import json

    (evidence / "facts-layout.json").write_text(json.dumps(measurements, indent=2))
    assert "Inter" in measurements["font"] and measurements["inputHeight"] >= 44


def test_owner_reuses_brand_examples_and_sourced_question(site, tmp_path):
    import json

    from playwright.sync_api import expect

    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    page.locator(".social-context-manual summary").click()
    page.get_by_label("¿Qué quieres ofrecer?", exact=True).fill("Producto sintético")
    page.get_by_label("Objetivo del negocio", exact=True).fill("Explicar cómo pedir")
    page.get_by_label("¿Cómo pueden comprar o pedir?", exact=True).fill("En el local de prueba")
    page.get_by_role("button", name="Añadir dato", exact=True).click()
    fact = page.locator(".social-fact").first
    fact.get_by_label("Nombre del dato", exact=True).fill("Cómo pedir")
    fact.get_by_label("Valor", exact=True).fill("Los pedidos de prueba se coordinan en el local.")
    deadline = (date.today() + timedelta(days=7)).isoformat()
    fact.get_by_label("Revisar antes de", exact=True).fill(deadline)
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    board = page.locator(".creative-board")
    board.locator("summary").click()
    board.get_by_role("button", name="Voz y estilo", exact=True).click()
    board.get_by_label("Dirección visual", exact=True).fill("Luz natural, producto protagonista.")
    board.get_by_label("Cómo hablamos", exact=True).fill(
        "Frases cortas. Sin prometer lo que no sabemos."
    )

    def save_board(reason, version):
        board.get_by_label("Motivo de este cambio", exact=True).fill(reason)
        board.get_by_label("Revisé las fuentes").check()
        board.get_by_role("button", name="Guardar referencias y preguntas", exact=True).click()
        expect(board.locator("summary")).to_contain_text("versión " + str(version))

    save_board("Dirección inicial para esta prueba", 1)
    board.get_by_role("button", name="Referencias", exact=True).click()
    for index, (title, judgment, group, reason) in enumerate(
        [
            ("Texto claro", "positive", "own_brand", "Explica el siguiente paso."),
            (
                "Promesa exagerada",
                "negative",
                "creative_reference",
                "No usar afirmaciones sin respaldo.",
            ),
            (
                "Otra panadería",
                "borderline",
                "remote_comparable",
                "La composición ayuda; su mercado no es comparable.",
            ),
        ],
        start=2,
    ):
        board.get_by_role("button", name="Añadir referencia", exact=True).click()
        board.get_by_label("Título de la referencia", exact=True).fill(title)
        board.get_by_label("Juicio de referencia", exact=True).select_option(judgment)
        board.get_by_label("Propósito de referencia", exact=True).select_option(group)
        board.get_by_label("Por qué encaja o no", exact=True).fill(reason)
        board.get_by_label("Ejemplo o descripción", exact=True).fill(
            "Texto sintético para evaluar una referencia."
        )
        board.get_by_label("Permiso para revisar este ejemplo", exact=True).fill(
            "Ejemplo propio creado para esta prueba."
        )
        board.get_by_label("Fuente y contexto", exact=True).fill("Kit sintético de evaluación")
        board.get_by_label("Volver a revisar antes de", exact=True).fill(deadline)
        save_board("Clasificar el ejemplo por su uso", index)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(evidence / "n03-reference-desktop.png"), full_page=True)
    board.get_by_role("button", name="Preguntas", exact=True).click()
    board.get_by_role("button", name="Añadir pregunta", exact=True).click()
    board.get_by_label("Pregunta a responder", exact=True).fill("¿Cómo hago un pedido?")
    board.get_by_label("Origen de la pregunta", exact=True).select_option("hypothesis")
    board.get_by_label("Siguiente paso útil", exact=True).fill("Consultar en el local de prueba")
    board.get_by_label("Los pedidos de prueba se coordinan en el local.", exact=True).check()
    board.get_by_label("Fuente y contexto", exact=True).fill(
        "Idea hipotética del operador; no es una pregunta observada."
    )
    board.get_by_label("Volver a revisar antes de", exact=True).fill(deadline)
    save_board("Probar una explicación de pedidos", 5)
    page.set_viewport_size({"width": 390, "height": 844})
    board.scroll_into_view_if_needed()
    page.screenshot(path=str(evidence / "n03-question-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.set_viewport_size({"width": 1440, "height": 1000})
    board.locator("summary").click()
    form = page.locator(".social-grid form")
    form.get_by_role("button", name="Usar objetivo del negocio", exact=True).click()
    form.get_by_role("button", name="Usar voz y estilo guardados", exact=True).click()
    form.get_by_label("Texto claro · nos gusta", exact=True).check()
    form.get_by_label("Pregunta guardada", exact=True).select_option(label="¿Cómo hago un pedido?")
    expect(form.get_by_label("¿Qué pregunta debe responder?", exact=True)).to_have_value(
        "¿Cómo hago un pedido?"
    )
    expect(form.get_by_label("Origen de esta pregunta", exact=True)).to_have_value("hypothesis")
    form.get_by_label("Revisar estos datos").fill(deadline)
    form.get_by_label("Permiso para usar").fill("Fotografía sintética autorizada para prueba")
    photo = tmp_path / "n03-fixture.jpg"
    Image.new("RGB", (1200, 1500), "#a49381").save(photo)
    form.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Preparar publicación", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    page.locator(".creative-receipt summary").click()
    expect(page.locator(".creative-receipt")).to_contain_text("Hipótesis por comprobar")
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    download.value.save_as(str(evidence / "n03-approved-package.zip"))
    import zipfile

    with zipfile.ZipFile(evidence / "n03-approved-package.zip") as z:
        saved = json.loads(z.read("editable.json"))
        assert saved["creative_snapshot"]["question"]["source_kind"] == "hypothesis"
        assert saved["creative_snapshot"]["search_volume"] is None
        assert saved["creative_snapshot"]["references"][0]["judgment"] == "positive"
    # Same source context is usable for a NEW pack after navigating away and back.
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.locator(".customer-link").first.wait_for()
    open_social(page)
    form.get_by_role("button", name="Usar objetivo del negocio", exact=True).click()
    form.get_by_role("button", name="Usar voz y estilo guardados", exact=True).click()
    form.get_by_label("Pregunta guardada", exact=True).select_option(label="¿Cómo hago un pedido?")
    expect(form.get_by_label("¿Cómo debe verse y sonar?")).to_have_value(
        "Luz natural, producto protagonista."
    )
    expect(form.get_by_label("¿Qué pregunta debe responder?", exact=True)).to_have_value(
        "¿Cómo hago un pedido?"
    )
    page.evaluate("window.scrollTo(0,0)")
    page.locator(".creative-board summary").click()
    page.screenshot(path=str(evidence / "n03-reuse-desktop.png"), full_page=True)
    measurements = page.locator(".creative-board").evaluate("""e=>({font:getComputedStyle(e).fontFamily,
        controlHeight:e.querySelector('button').getBoundingClientRect().height,
        overflow:document.documentElement.scrollWidth>innerWidth})""")
    (evidence / "n03-layout.json").write_text(json.dumps(measurements, indent=2))
    assert "Inter" in measurements["font"] and measurements["controlHeight"] >= 44
    # Business changes also clear brand/question context.
    page.locator(".sidebar select").select_option(OTHER)
    expect(page.get_by_label("¿Qué pregunta debe responder?", exact=True)).to_have_value("")
    assert form.get_by_role("button", name="Usar voz y estilo guardados", exact=True).count() == 0


def test_guided_onboarding_custom_reuse_and_unknowns(site, tmp_path):
    import json

    from playwright.sync_api import expect

    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    guide = page.get_by_role("region", name="Guía de tu negocio")
    guide.get_by_role("heading", name="¿Qué te gustaría conseguir primero?").wait_for()
    assert guide.locator("input:checked").count() == 0
    guide.screenshot(path=str(evidence / "onboarding-start-desktop.png"))
    guide.get_by_role("button", name="Continuar", exact=True).click()
    expect(guide.get_by_role("alert")).to_contain_text("Elige una respuesta")
    guide.get_by_label("Recibir más pedidos", exact=True).check()
    guide.get_by_role("button", name="Continuar", exact=True).click()
    guide.get_by_label("Por WhatsApp", exact=True).check()
    guide.get_by_label("Por WhatsApp · dirección").fill("Número por confirmar")
    guide.get_by_label("Otra forma", exact=True).check()
    guide.get_by_label("Describe la otra forma de comprar").fill(
        "Por encargo en nuestra feria de prueba"
    )
    page.set_viewport_size({"width": 390, "height": 844})
    guide.scroll_into_view_if_needed()
    guide.screenshot(path=str(evidence / "onboarding-channels-mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    guide.get_by_role("button", name="Continuar", exact=True).click()
    guide.get_by_label("Un producto o servicio", exact=True).check()
    guide.get_by_role("button", name="Continuar", exact=True).click()
    expect(guide.get_by_role("heading")).to_have_text("¿Qué te gustaría mostrar primero?")
    guide.get_by_label("¿Qué quieres mostrar o explicar?").fill(
        "Una pieza sintética para esta prueba"
    )
    guide.get_by_role("button", name="Continuar", exact=True).click()
    guide.get_by_label("Fotos", exact=True).check()
    guide.get_by_label("Otro material", exact=True).check()
    guide.get_by_label("Describe el otro material").fill("Catálogo de prueba")
    guide.get_by_role("button", name="Continuar", exact=True).click()
    guide.locator(".onboarding-extra summary").click()
    guide.get_by_label("Trabajamos por encargo", exact=True).check()
    guide.get_by_label("Depende del producto", exact=True).check()
    guide.get_by_label("Detalles del plazo").fill("Confirmamos el plazo de cada encargo")
    guide.get_by_label("Idioma y región").fill("es-CO")
    expect(guide.get_by_role("button", name="Guardar mis respuestas")).to_be_disabled()
    guide.get_by_label("Revisé mis respuestas.").check()
    # Editing after confirmation requires a fresh confirmation.
    guide.get_by_label("Detalles del plazo").fill("El plazo sigue pendiente para cada encargo")
    expect(guide.get_by_role("button", name="Guardar mis respuestas")).to_be_disabled()
    guide.screenshot(path=str(evidence / "onboarding-review-mobile.png"))
    guide.get_by_label("Revisé mis respuestas.").check()
    guide.get_by_role("button", name="Guardar mis respuestas").click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    api = "/api/operator/restaurants/" + BUSINESS + "/social"
    saved = page.request.get(api + "/context").json()
    assert saved["facts"] == []
    assert saved["onboarding"]["channels"][1]["detail"] == "Por encargo en nuestra feria de prueba"
    assert saved["brief"]["capacity"] is None
    # Reload is genuine persistence, not component state.
    page.reload()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    if not page.locator(".business-context").evaluate("e=>e.open"):
        page.locator(".business-context > summary").click()
    page.get_by_role("button", name="Responder con opciones", exact=True).click()
    expect(guide.get_by_label("Recibir más pedidos", exact=True)).to_be_checked()
    guide.get_by_role("button", name="Continuar", exact=True).click()
    expect(guide.get_by_label("Describe la otra forma de comprar")).to_have_value(
        "Por encargo en nuestra feria de prueba"
    )
    guide.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    # Add one separately confirmed fact, then use the saved goal in a real photo pack.
    manual = page.locator(".social-context-manual")
    if not manual.evaluate("e=>e.open"):
        manual.locator("summary").click()
    page.get_by_role("button", name="Añadir dato", exact=True).click()
    fact = page.locator(".social-fact").first
    fact.get_by_label("Nombre del dato", exact=True).fill("Descripción")
    fact.get_by_label("Valor", exact=True).fill("Imagen sintética de prueba.")
    fact.get_by_label("Revisar antes de", exact=True).fill(
        (date.today() + timedelta(days=7)).isoformat()
    )
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.get_by_text("Información de tu negocio · versión 2", exact=True).wait_for()
    assert page.request.get(api + "/context").json()["onboarding"] == saved["onboarding"]
    page.get_by_role("button", name="Usar objetivo del negocio", exact=True).click()
    expect(page.get_by_label("¿Qué quieres conseguir?", exact=True)).to_have_value(
        "Recibir más pedidos"
    )
    page.locator("#social-production-form").get_by_label(
        "Imagen sintética de prueba.", exact=True
    ).check()
    page.get_by_label("¿Qué pregunta debe responder?", exact=True).fill(
        "¿Qué muestra la imagen de prueba?"
    )
    page.get_by_label("Revisar estos datos").fill((date.today() + timedelta(days=7)).isoformat())
    page.get_by_label("¿Cómo debe verse y sonar?").fill("Claro y natural")
    page.get_by_label("Permiso para usar").fill("Material sintético creado para esta prueba")
    photo = tmp_path / "onboarding-fixture.jpg"
    Image.new("RGB", (1200, 1500), "#9b8876").save(photo)
    page.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Preparar publicación", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    expect(page.locator("aside .social-caption")).to_have_text("Imagen sintética de prueba.")
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    download.value.save_as(str(evidence / "onboarding-approved-package.zip"))
    page.set_viewport_size({"width": 1440, "height": 1000})
    # Actual voice examples update the existing separate board only after review.
    page.locator(".creative-board summary").click()
    page.get_by_role("button", name="Voz y estilo", exact=True).click()
    page.get_by_role("button", name="Cercano y conversado", exact=False).click()
    assert "cercana y conversada" in page.get_by_label("Cómo hablamos", exact=True).input_value()
    page.get_by_label("Cómo hablamos", exact=True).fill(
        "Hablar con calma y sin exageraciones. Preferencia sintética."
    )
    page.get_by_label("Motivo de este cambio").fill("Prueba de elección y adaptación del tono")
    page.get_by_label("Revisé las fuentes").check()
    page.get_by_role("button", name="Guardar referencias y preguntas", exact=True).click()
    page.get_by_text("Referencias, voz y preguntas · versión 1", exact=True).wait_for()
    page.screenshot(path=str(evidence / "onboarding-voice-desktop.png"), full_page=True)
    # Business switching discards unsaved intake, and unknown answers stay null.
    page.locator(".sidebar select").select_option(OTHER)
    guide.get_by_role("heading", name="¿Qué te gustaría conseguir primero?").wait_for()
    assert guide.locator("input:checked").count() == 0
    for answer in [
        "No estoy seguro",
        "Lo vemos después",
        "Ayúdenme a decidir",
        "Todavía no tengo material",
    ]:
        guide.get_by_label(answer, exact=True).check()
        guide.get_by_role("button", name="Continuar", exact=True).click()
    guide.get_by_label("Revisé mis respuestas.").check()
    guide.get_by_role("button", name="Guardar mis respuestas").click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    unknown = page.request.get(api.replace(BUSINESS, OTHER) + "/context").json()
    assert unknown["facts"] == []
    assert all(
        unknown["brief"][key] is None
        for key in ("objective", "offering", "buying_destination", "locale")
    )
    (evidence / "onboarding-result.json").write_text(
        json.dumps(
            {"saved": saved, "unknown": unknown, "provider_calls": 0, "fixture": True},
            ensure_ascii=False,
            indent=2,
        )
    )


def test_durable_job_retry_and_return_to_result(site, tmp_path):
    import json

    from playwright.sync_api import expect
    from world_model.restaurant_commerce import social_jobs

    page, context, url, app, *_ = site
    app.state.social_worker_paused = True
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("region", name="Guía de tu negocio").wait_for()
    page.get_by_label("¿Qué quieres conseguir?", exact=True).fill("Explicar esta imagen sintética")
    page.get_by_label("¿Qué pregunta debe responder?", exact=True).fill("¿Qué muestra?")
    page.get_by_label("Texto que puedes confirmar").fill(
        "Archivo sintético para probar la recuperación."
    )
    page.get_by_label("Revisar estos datos").fill((date.today() + timedelta(days=7)).isoformat())
    page.get_by_label("¿Cómo debe verse y sonar?").fill("Natural y claro")
    page.get_by_label("Permiso para usar").fill("Material sintético creado para esta prueba")
    photo = tmp_path / "queue.jpg"
    Image.new("RGB", (1200, 1500), "#9b8876").save(photo)
    page.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Preparar publicación", exact=True).click()
    panel = page.get_by_role("region", name="Preparación de contenido")
    expect(panel).to_contain_text("En cola")
    page.screenshot(path=str(evidence / "n04-queued-desktop.png"), full_page=True)
    root = "/api/operator/restaurants/" + BUSINESS + "/social"
    job = page.request.get(root + "/jobs").json()["jobs"][0]
    pair = social_jobs.claim(app.state.session_factory, job_id=job["id"])
    social_jobs.failed(app.state.session_factory, *pair, RuntimeError("Synthetic one-time failure"))
    expect(panel).to_contain_text("No se pudo terminar")
    panel.get_by_role("button", name="Ver actividad", exact=True).click()
    expect(panel).to_contain_text("Costo de procesamiento y almacenamiento: sin calcular")
    page.set_viewport_size({"width": 390, "height": 844})
    panel.screenshot(path=str(evidence / "n04-failed-mobile.png"))
    panel.get_by_role("button", name="Reintentar este paso", exact=True).click()
    expect(panel).to_contain_text("En cola")
    # Leave the route while the saved task is queued. Worker completes independently.
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("link", name="Clientes", exact=True).click()
    page.locator(".customer-link").first.wait_for()
    assert social_jobs.dispatch_one(app.state.session_factory, app)
    open_social(page)
    panel.get_by_role("button", name="Abrir resultado", exact=True).wait_for()
    panel.get_by_role("button", name="Abrir resultado", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    assert (
        page.locator("aside .social-caption").inner_text()
        == "Archivo sintético para probar la recuperación."
    )
    panel.get_by_role("button", name="Ver actividad", exact=True).click()
    panel.get_by_label("Tiempo dedicado (segundos)").fill("45")
    panel.get_by_role("button", name="Registrar tiempo", exact=True).click()
    expect(panel).to_contain_text("45 s")
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    download.value.save_as(str(evidence / "n04-approved-package.zip"))
    panel.screenshot(path=str(evidence / "n04-recovered-desktop.png"))
    layout = panel.evaluate(
        """e=>({font:getComputedStyle(e).fontFamily,buttonHeight:e.querySelector('button').getBoundingClientRect().height})"""
    )
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    layout["mobileOverflow"] = False
    (evidence / "n04-layout.json").write_text(json.dumps(layout))
    done = page.request.get(root + "/jobs/" + job["id"]).json()
    assert [a["state"] for a in done["attempts"]] == ["failed", "succeeded"]
    assert done["cost"]["total_microusd"] is None
    (evidence / "n04-job.json").write_text(json.dumps(done, indent=2))


def test_owner_reviews_two_proposals_and_produces_exact_selected_copy(site, tmp_path):
    """N05 normal UI, template mode explicitly labeled; no API fixture shortcut."""
    import json
    import zipfile

    from playwright.sync_api import expect

    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    page.locator(".social-context-manual summary").click()
    page.get_by_label("¿Qué quieres ofrecer?", exact=True).fill("Producto sintético")
    page.get_by_label("Objetivo del negocio", exact=True).fill("Explicar cómo pedir")
    page.get_by_label("¿Cómo pueden comprar o pedir?", exact=True).fill("En el local de prueba")
    page.get_by_role("button", name="Añadir dato", exact=True).click()
    fact = page.locator(".social-fact").first
    fact.get_by_label("Nombre del dato", exact=True).fill("Precio")
    fact.get_by_label("Tipo", exact=True).select_option("money")
    fact.get_by_label("Valor", exact=True).fill("12000")
    fact.get_by_label("Moneda", exact=True).fill("COP")
    fact.get_by_label("Revisar antes de", exact=True).fill(
        (date.today() + timedelta(days=7)).isoformat()
    )
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    page.get_by_label("Revisar estos datos").fill((date.today() + timedelta(days=7)).isoformat())
    photo = tmp_path / "proposal-fixture.png"
    Image.new("RGB", (1200, 1500), "#998877").save(photo)
    page.get_by_label("Permiso para usar").fill("Imagen sintética creada para esta prueba.")
    page.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    panel = page.locator(".proposal-panel")
    panel.locator("summary").first.click()
    panel.get_by_label("Fotografía para esta idea").select_option(index=1)
    panel.get_by_label("Precio: 12000 COP.", exact=True).check()
    panel.get_by_label("Pregunta o tema").fill("¿Cuánto cuesta?")
    panel.get_by_role("button", name="Preparar propuesta y dos textos", exact=True).click()
    panel.get_by_role("button", name="Elegir texto conversado", exact=True).wait_for()
    assert "No se llamó a un modelo." in panel.inner_text()
    assert panel.locator(".proposal-options article").count() == 2
    panel.get_by_role("button", name="Elegir texto conversado", exact=True).click()
    text = panel.get_by_label("Texto elegido · puedes editarlo", exact=True)
    text.fill("Precio: 15000 COP.")
    panel.get_by_label("Comprobé cada afirmación").check()
    panel.get_by_label("Revisé el texto completo").check()
    panel.get_by_label("Motivo de la decisión").fill("Prueba de corrección de precio")
    panel.get_by_role("button", name="Guardar texto revisado", exact=True).click()
    expect(panel.get_by_role("alert")).to_contain_text("sin respaldo")
    selected = "Te contamos el precio.\n\nPrecio: 12000 COP."
    text.fill(selected)
    panel.get_by_label("Comprobé cada afirmación").check()
    panel.get_by_label("Revisé el texto completo").check()
    panel.get_by_label("Tipo de decisión").select_option("style_preference")
    panel.get_by_label("Motivo de la decisión").fill("Una entrada más clara para esta prueba")
    panel.get_by_role("button", name="Guardar texto revisado", exact=True).click()
    panel.get_by_role("button", name="Preparar publicación con este texto", exact=True).wait_for()
    page.screenshot(path=str(evidence / "proposal-desktop-after.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(evidence / "proposal-mobile-selected.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    metrics = panel.evaluate("""e => ({font:getComputedStyle(e).fontFamily,
        width:e.getBoundingClientRect().width,
        actionHeights:[...e.querySelectorAll('button')].filter(x=>x.offsetParent).map(x=>x.getBoundingClientRect().height),
        overflow:document.documentElement.scrollWidth>innerWidth})""")
    (evidence / "proposal-layout.json").write_text(json.dumps(metrics, indent=2))
    assert "Inter" in metrics["font"] and min(metrics["actionHeights"]) >= 44
    panel.get_by_role("button", name="Preparar publicación con este texto", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    assert page.locator("aside .social-caption").inner_text() == selected
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    package = evidence / "proposal-approved-package.zip"
    download.value.save_as(str(package))
    with zipfile.ZipFile(package) as z:
        assert z.read("caption.txt").decode() == selected
        (evidence / "proposal-post.jpg").write_bytes(z.read("post.jpg"))
    # Crop revision preserves the reviewed copy, hypothesis and intended measure.
    pack_id = page.get_by_label("Trabajo guardado").input_value()
    api = "/api/operator/restaurants/" + BUSINESS + "/social/packs/" + pack_id
    before = page.request.get(api).json()
    page.get_by_label("Encuadre horizontal").fill("0.3")
    page.get_by_label("Confirmo que").check()
    page.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2").wait_for()
    after = page.request.get(api).json()
    assert after["document"]["caption"] == selected and not after["approved"]
    for field in ("hypothesis", "primary_measure"):
        assert after["document"]["brief"][field] == before["document"]["brief"][field]
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(path=str(evidence / "proposal-approved-desktop.png"), full_page=True)
    page.reload()
    page.locator(".proposal-panel > summary").click()
    panel.get_by_label("Propuestas guardadas").select_option(index=1)
    panel.get_by_role("button", name="Preparar publicación con este texto", exact=True).wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(evidence / "proposal-mobile-after.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_owner_edits_static_layers_corrects_price_and_views_history(
    site, tmp_path, caption_from_price=True
):
    """Real owner UI → actual licensed typography → corrected price without photo/layout loss."""
    import io
    import json
    import zipfile
    from PIL import ImageDraw
    from playwright.sync_api import expect

    page, context, url, app, *_ = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    page.locator(".social-context-manual summary").click()
    page.get_by_label("¿Qué quieres ofrecer?", exact=True).fill(
        "Material sintético para verificar el diseño"
    )
    page.get_by_label("Objetivo del negocio", exact=True).fill("Explicar una pieza de prueba")
    page.get_by_label("¿Cómo pueden comprar o pedir?", exact=True).fill(
        "Ruta de prueba sin publicación"
    )
    page.get_by_role("button", name="Añadir dato", exact=True).click()
    fact = page.locator(".social-fact").first
    fact.get_by_label("Nombre del dato", exact=True).fill("Precio")
    fact.get_by_label("Tipo", exact=True).select_option("money")
    fact.get_by_label("Valor", exact=True).fill("12000")
    fact.get_by_label("Moneda", exact=True).fill("COP")
    deadline = (date.today() + timedelta(days=7)).isoformat()
    fact.get_by_label("Revisar antes de", exact=True).fill(deadline)
    page.get_by_label("He revisado esta información").check()
    page.get_by_role("button", name="Guardar información del negocio", exact=True).click()
    page.get_by_text("Información de tu negocio · versión 1", exact=True).wait_for()
    form = page.locator("#social-production-form")
    form.get_by_role("button", name="Usar objetivo del negocio", exact=True).click()
    if caption_from_price:
        form.get_by_label("Precio: 12000 COP.", exact=True).check()
    else:
        form.get_by_label("Texto que puedes confirmar", exact=True).fill(
            "Imagen sintética para esta prueba."
        )
    form.get_by_label("¿Qué pregunta debe responder?", exact=True).fill(
        "¿Cuál es el precio de esta pieza de prueba?"
    )
    form.get_by_label("Revisar estos datos").fill(deadline)
    form.get_by_label("¿Cómo debe verse y sonar?").fill(
        "Foto real sin retoques, título legible y precio confirmado."
    )
    form.get_by_label("Permiso para usar").fill(
        "Fixture geométrico creado por el autor de esta prueba."
    )
    source = Image.new("RGB", (1200, 1500), "#d4c4ac")
    draw = ImageDraw.Draw(source)
    draw.rectangle((0, 1000, 1200, 1500), fill="#b1b69f")
    draw.ellipse((180, 210, 1080, 1110), fill="#b76d4d")
    draw.ellipse((310, 340, 950, 980), fill="#e8dac5")
    photo = tmp_path / "canvas-fixture.png"
    source.save(photo)
    form.locator("input[type=file]").set_input_files(str(photo))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    editor = page.locator(".social-design-editor")
    editor.locator("summary").first.click()
    editor.get_by_label("Composición", exact=True).select_option("photo_first")
    title = "Una imagen para explicar el próximo paso"
    editor.get_by_label("Título de la imagen", exact=True).fill(title)
    editor.get_by_label("Precio · dato o texto", exact=True).select_option(
        label="Precio: 12000 COP."
    )
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Preparar publicación", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1").wait_for()
    packid = page.get_by_label("Trabajo guardado").input_value()
    api = "/api/operator/restaurants/" + BUSINESS + "/social/packs/" + packid
    before = page.request.get(api).json()
    first_image = page.request.get(api + "/image").body()
    assert before["document"]["design"]["layers"][-1]["text"] == "Precio: 12000 COP."
    if not caption_from_price:
        price_id = before["document"]["design"]["layers"][-1]["fact_id"]
        assert price_id not in before["document"]["brief"]["caption_fact_ids"]
        assert price_id in [r["fact_id"] for r in before["document"]["brief"]["fact_refs"]]
    page.locator("aside .social-image").screenshot(path=str(evidence / "photo-first-12000.png"))
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    form.get_by_role("link", name="Ver imagen preparada · versión 1", exact=True).click()
    page.screenshot(path=str(evidence / "design-review-desktop-after.png"), full_page=False)
    page.get_by_role("link", name="Volver a editar el diseño", exact=True).click()
    editor.screenshot(path=str(evidence / "design-editor-desktop-after.png"))
    page.screenshot(path=str(evidence / "design-desktop-after.png"), full_page=True)
    # Overflow is actionable and cannot create a misleading successful version.
    editor.get_by_label("Título de la imagen", exact=True).fill("Texto de prueba " * 18)
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("no cabe")
    assert page.request.get(api).json()["revision"] == 1
    editor.get_by_label("Título de la imagen", exact=True).fill(title)
    editor.get_by_label("Nuevo precio confirmado").fill("15000")
    editor.get_by_label("Confirmo este nuevo precio.", exact=True).check()
    editor.get_by_role("button", name="Actualizar precio del negocio", exact=True).click()
    page.locator(".social-stale").wait_for()
    assert page.get_by_role("link", name="Descargar foto", exact=False).count() == 0
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2").wait_for()
    after = page.request.get(api).json()
    a, b = before["document"]["design"], after["document"]["design"]
    assert a["layers"][1] == b["layers"][1] and a["styles"] == b["styles"]
    assert a["layers"][2] == b["layers"][2] and b["layers"][-1]["text"] == "Precio: 15000 COP."
    assert not after["approved"]
    page.locator("aside .social-image").screenshot(path=str(evidence / "photo-first-15000.png"))
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    package = evidence / "photo-first-package.zip"
    download.value.save_as(str(package))
    with zipfile.ZipFile(package) as z:
        (evidence / "photo-first-final.jpg").write_bytes(z.read("post.jpg"))
        assert json.loads(z.read("design.json")) == b
        assert z.read("caption.txt").decode() == (
            "Precio: 15000 COP." if caption_from_price else "Imagen sintética para esta prueba."
        )
    editor.get_by_label("Composición", exact=True).select_option("information")
    editor.get_by_label("Color del fondo", exact=True).fill("#253b39")
    editor.get_by_label("Color del texto", exact=True).fill("#f5f1e9")
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 3").wait_for()
    page.get_by_label("Revisé la fotografía").check()
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada").wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    package = evidence / "information-package.zip"
    download.value.save_as(str(package))
    with zipfile.ZipFile(package) as z:
        (evidence / "information-final.jpg").write_bytes(z.read("post.jpg"))
    information = page.request.get(api).json()
    # Independent photo replacement preserves the composed typography and text.
    second = tmp_path / "replacement.png"
    Image.new("RGB", (1400, 1700), "#b2bed0").save(second)
    form.locator("input[type=file]").set_input_files(str(second))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    form.get_by_label("Confirmo que").check()
    form.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 4").wait_for()
    final = page.request.get(api).json()
    assert final["document"]["design"]["styles"] == information["document"]["design"]["styles"]
    assert (
        final["document"]["design"]["layers"][2:] == information["document"]["design"]["layers"][2:]
    )
    assert (
        final["document"]["design"]["layers"][1]["asset_id"]
        != information["document"]["design"]["layers"][1]["asset_id"]
    )
    history = page.locator(".social-design-history")
    history.locator("summary").click()
    history.get_by_role("button", name="Ver imagen y texto 1", exact=True).click()
    expect(
        history.get_by_text(
            "Precio: 12000 COP." if caption_from_price else "Imagen sintética para esta prueba.",
            exact=True,
        )
    ).to_be_visible()
    assert page.request.get(api + "/revisions/1/image").body() == first_image
    page.screenshot(path=str(evidence / "design-history-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    editor.scroll_into_view_if_needed()
    editor.screenshot(path=str(evidence / "design-editor-mobile-after.png"))
    page.screenshot(path=str(evidence / "design-mobile-after.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    metrics = editor.evaluate("""e=>({font:getComputedStyle(e).fontFamily,
      actionHeights:[...e.querySelectorAll('button')].filter(x=>x.offsetParent).map(x=>x.getBoundingClientRect().height),
      overflow:document.documentElement.scrollWidth>innerWidth})""")
    (evidence / "design-layout.json").write_text(json.dumps(metrics, indent=2))
    assert "Inter" in metrics["font"] and min(metrics["actionHeights"]) >= 44
    page.reload()
    page.get_by_label("Trabajo guardado").select_option(packid)
    page.get_by_role("heading", name="Revisa la versión 4").wait_for()
    assert editor.get_by_label("Composición", exact=True).input_value() == "information"
    assert editor.get_by_label("Título de la imagen", exact=True).input_value() == title


def test_owner_price_only_in_design_stales_without_caption_dependency(site, tmp_path, monkeypatch):
    directory = (
        Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence"))) / "overlay-only"
    )
    monkeypatch.setenv("SOCIAL_BROWSER_EVIDENCE", str(directory))
    test_owner_edits_static_layers_corrects_price_and_views_history(
        site, tmp_path, caption_from_price=False
    )
