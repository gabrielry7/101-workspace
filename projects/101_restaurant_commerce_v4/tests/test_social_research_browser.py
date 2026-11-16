"""Normal browser controls from sourced research to a reviewed ZIP; synthetic kit."""

# ruff: noqa: F401,F811 -- imported pytest fixtures
import json
import os
import zipfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect
from test_browser_security import browser, playwright
from test_combined_workspace_browser import site
from test_social_workspace_browser import BUSINESS, PASSWORD, complete_review


def test_owner_research_search_plan_and_advisory_review(site, tmp_path):
    page, _, _, app, errors, external, csp = site
    evidence = Path(os.environ.get("SOCIAL_BROWSER_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=True)
    page.goto("/workspace/social?business=" + BUSINESS)
    page.get_by_label("Usuario", exact=True).fill("multi.owner")
    page.get_by_label("Contraseña", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("heading", name="Contenido para tus redes").wait_for()
    page.get_by_role("button", name="Cerrar sin guardar", exact=True).click()
    page.screenshot(path=str(evidence / "n11-before-desktop.png"), full_page=True)
    page.locator(".social-context-manual summary").click()
    page.get_by_label("¿Qué quieres ofrecer?", exact=True).fill("Producto sintético")
    page.get_by_label("Objetivo del negocio", exact=True).fill("Explicar el precio")
    page.get_by_label("¿Cómo pueden comprar o pedir?", exact=True).fill("En el local de prueba")
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
    board = page.locator(".creative-board")
    board.locator("summary").click()
    board.get_by_role("button", name="Referencias", exact=True).click()
    board.get_by_role("button", name="Añadir referencia", exact=True).click()
    board.get_by_label("Título de la referencia", exact=True).fill("Referencia sintética")
    board.get_by_label("Propósito de referencia", exact=True).select_option("remote_comparable")
    board.get_by_label("Por qué encaja o no", exact=True).fill(
        "La explicación es clara, no conocemos sus ventas."
    )
    board.get_by_label("Ejemplo o descripción", exact=True).fill(
        "Referencia propia escrita para esta prueba."
    )
    board.get_by_label("Permiso para revisar este ejemplo", exact=True).fill(
        "Texto propio, solo referencia interna."
    )
    board.get_by_label("Fuente y contexto", exact=True).fill("Kit sintético, no una cuenta real")
    board.get_by_label("Volver a revisar antes de", exact=True).fill(deadline)

    def save_brand(reason, version):
        board.get_by_label("Motivo de este cambio", exact=True).fill(reason)
        board.get_by_label("Revisé las fuentes").check()
        board.get_by_role("button", name="Guardar referencias y preguntas", exact=True).click()
        expect(board.locator("summary")).to_contain_text("versión " + str(version))

    save_brand("Guardar referencia sintética", 1)
    board.get_by_role("button", name="Preguntas", exact=True).click()
    board.get_by_role("button", name="Añadir pregunta", exact=True).click()
    board.get_by_label("Pregunta a responder", exact=True).fill("¿Cuánto cuesta?")
    board.get_by_label("Origen de la pregunta", exact=True).select_option("customer_question")
    board.get_by_label("Siguiente paso útil", exact=True).fill("Consultar en el local de prueba")
    board.get_by_label("Precio: 12000 COP.", exact=True).check()
    board.get_by_label("Fuente y contexto", exact=True).fill(
        "Pregunta sintética autorizada, no demanda medida"
    )
    board.get_by_label("Volver a revisar antes de", exact=True).fill(deadline)
    save_brand("Guardar pregunta de prueba", 2)
    board.locator("summary").click()
    page.get_by_label("Revisar estos datos").fill(deadline)
    image = tmp_path / "research-fixture.png"
    Image.new("RGB", (1200, 1500), "#998877").save(image)
    page.get_by_label("Permiso para usar").fill("Fotografía sintética propia de esta prueba.")
    page.locator("input[type=file]").set_input_files(str(image))
    page.get_by_text("Fotografía recibida.", exact=True).wait_for()
    research = page.locator(".social-research")
    research.locator("summary").first.click()
    research.get_by_role("button", name="Añadir publicación de referencia", exact=True).click()
    form = research.locator(".research-editor")
    form.get_by_label("Referencia o cuenta", exact=True).select_option(index=1)
    form.get_by_label("Cuenta observada", exact=True).fill("fixture-account")
    form.get_by_label("Asunto de la publicación", exact=True).fill("Explicación del producto")
    form.get_by_label("Fuente de esta observación", exact=True).fill(
        "Anotación sintética de una referencia, sin acceso a una cuenta"
    )
    form.get_by_label("Qué observamos", exact=True).fill(
        "El ejemplo muestra un producto y una explicación."
    )
    form.get_by_label("Qué podría explicarlo · hipótesis", exact=True).fill(
        "La explicación podría ayudar a entenderlo."
    )
    form.get_by_label("Otras explicaciones posibles", exact=True).fill(
        "No sabemos si tuvo apoyo pagado ni resultados."
    )
    form.get_by_label("Qué podríamos probar con nuestro material", exact=True).fill(
        "Mostrar el producto real y responder su precio."
    )

    def save_source():
        form.get_by_label("Permiso y uso de esta fuente", exact=True).fill(
            "Apuntes sintéticos propios, solo referencia interna."
        )
        form.get_by_label("Revisar esta observación antes de", exact=True).fill(deadline)
        form.get_by_label("Revisé la fuente, las fechas y el permiso").check()
        form.get_by_role("button", name="Guardar observación", exact=True).click()
        expect(form).to_have_count(0)

    save_source()
    research.get_by_label("Usar evidencia: Explicación del producto", exact=True).check()
    research.get_by_role("button", name="Añadir observación de búsqueda", exact=True).click()
    form = research.locator(".research-editor")
    form.get_by_label("Pregunta que investigamos", exact=True).select_option(index=1)
    form.get_by_label("Fuente de esta observación", exact=True).fill(
        "Pregunta sintética recibida con permiso"
    )
    form.get_by_label("Qué observamos", exact=True).fill(
        "Una persona preguntó por el precio en este ejemplo."
    )
    form.get_by_label("Origen de la observación", exact=True).select_option("customer_question")
    form.get_by_label("Idioma y región de la búsqueda", exact=True).fill("es-CO")
    form.get_by_label("Contexto de la observación", exact=True).fill(
        "Caso de desarrollo, no buscador ni volumen real"
    )
    save_source()
    research.get_by_label("Usar búsqueda: ¿Cuánto cuesta?", exact=True).check()
    research.scroll_into_view_if_needed()
    page.screenshot(path=str(evidence / "n11-research-desktop.png"), full_page=True)
    research.screenshot(path=str(evidence / "n11-research-panel-desktop.png"))
    page.set_viewport_size(dict(width=390, height=844))
    research.scroll_into_view_if_needed()
    page.screenshot(path=str(evidence / "n11-research-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    measures = research.evaluate(
        """e=>({font:getComputedStyle(e).fontFamily,buttons:[...e.querySelectorAll('button')].filter(x=>x.offsetParent).map(x=>x.getBoundingClientRect().height),width:e.getBoundingClientRect().width,overflow:document.documentElement.scrollWidth>innerWidth})"""
    )
    assert "Inter" in measures["font"] and min(measures["buttons"]) >= 44
    research.get_by_role("button", name="Preparar propuesta con esta evidencia", exact=True).click()
    panel = page.locator(".proposal-panel")
    panel.get_by_label("Fotografía para esta idea").select_option(index=1)
    panel.get_by_role("button", name="Preparar propuesta y dos textos", exact=True).click()
    panel.get_by_role("button", name="Elegir texto conversado", exact=True).wait_for()
    expect(panel).to_contain_text("Pregunta y respuesta para esta pieza")
    expect(panel).to_contain_text("12000 COP")
    panel.get_by_role("button", name="Elegir texto conversado", exact=True).click()
    panel.get_by_label("Comprobé cada afirmación").check()
    panel.get_by_label("Revisé el texto completo").check()
    panel.get_by_label("Motivo de la decisión", exact=True).fill(
        "Revisión de un texto con fuentes de prueba."
    )
    panel.get_by_role("button", name="Guardar texto revisado", exact=True).click()
    panel.get_by_role("button", name="Preparar publicación con este texto", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 1", exact=True).wait_for()
    # The normal editor preserves the researched proposal while adding actual
    # editable type layers; this is not a disconnected photo-only demo.
    editor = page.locator(".social-design-editor")
    editor.locator("summary").first.click()
    editor.get_by_label("Composición", exact=True).select_option("photo_first")
    editor.get_by_label("Título de la imagen", exact=True).fill("Una respuesta para elegir")
    editor.get_by_label("Precio · dato o texto", exact=True).select_option(
        label="Precio: 12000 COP."
    )
    production_form = page.locator("#social-production-form")
    production_form.get_by_label("Confirmo que").check()
    production_form.get_by_role("button", name="Guardar nueva versión", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2", exact=True).wait_for()
    check = page.get_by_role("region", name="Comprobaciones de preparación")
    check.get_by_role("button", name="Comprobar esta versión", exact=True).click()
    check.get_by_text("Comprobaciones locales terminadas", exact=True).wait_for()
    expect(check.get_by_role("heading")).to_have_count(6)
    page.set_viewport_size(dict(width=1440, height=1000))
    check.scroll_into_view_if_needed()
    page.screenshot(path=str(evidence / "n11-review-desktop.png"), full_page=True)
    check.get_by_text("¿Fue útil esta comprobación?", exact=True).click()
    check.get_by_label("Tu evaluación de la comprobación", exact=True).select_option("helpful")
    check.get_by_label("Tipo de corrección de la comprobación", exact=True).select_option(
        "technical"
    )
    check.get_by_label("Por qué", exact=True).fill(
        "Distingue comprobaciones de archivo y juicio creativo."
    )
    check.get_by_role("button", name="Guardar evaluación", exact=True).click()
    complete_review(page)
    page.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    page.get_by_role("button", name="Versión aprobada", exact=True).wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar foto", exact=False).click()
    package = evidence / "n11-approved-fixture.zip"
    download.value.save_as(str(package))
    with zipfile.ZipFile(package) as z:
        assert json.loads(z.read("research.json"))["searches"][0]["query"] == "¿Cuánto cuesta?"
        assert json.loads(z.read("automated-review.json"))["reviews"][0]["output"][
            "human_review_required"
        ]
        assert json.loads(z.read("design.json"))["layers"][-1]["text"] == "Precio: 12000 COP."
        (evidence / "n11-fixture-post.jpg").write_bytes(z.read("post.jpg"))
    page.set_viewport_size(dict(width=390, height=844))
    check.scroll_into_view_if_needed()
    page.screenshot(path=str(evidence / "n11-review-mobile.png"), full_page=True)
    check.screenshot(path=str(evidence / "n11-review-panel-mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    measures["review"] = check.evaluate("""e=>{
      const s=getComputedStyle(e), bg=getComputedStyle(e.closest('aside'));
      const rgb=c=>c.match(/[\\d.]+/g).slice(0,3).map(Number);
      const lum=c=>rgb(c).map(v=>{v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
      const a=lum(s.color),b=lum(bg.backgroundColor);
      return {font:s.fontFamily,color:s.color,background:bg.backgroundColor,contrast:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
    }""")
    assert measures["review"]["contrast"] >= 4.5
    # Correcting an actual source through its controls invalidates the approved
    # result and advisory report; the next proposal must use the current source.
    research.get_by_role(
        "button", name="Editar observación: Explicación del producto", exact=True
    ).click()
    form = research.locator(".research-editor")
    expect(form).to_be_visible()
    form.get_by_label("Qué observamos", exact=True).fill(
        "Corregimos esta observación sintética después de la revisión."
    )
    save_source()
    page.get_by_role(
        "button", name="Revisar investigación y preparar otra propuesta", exact=True
    ).wait_for()
    expect(check).to_contain_text(
        "Esta comprobación corresponde a una versión o fuentes que cambiaron."
    )
    assert page.get_by_role("link", name="Descargar foto", exact=False).count() == 0
    (evidence / "n11-layout.json").write_text(json.dumps(measures, indent=2))
    assert not errors and not external and not csp
