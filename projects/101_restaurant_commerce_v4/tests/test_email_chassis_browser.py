"""Actual campaign editor -> reusable visual config -> revision -> approval."""

# ruff: noqa: F401,F811
import json
import os
from pathlib import Path

import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright
from test_workspace_views_browser import site


def test_chassis_export_import_apply_edit_and_reapprove(site, tmp_path):
    page, context, url, app, errors, external, csp = site
    out = Path(os.environ.get("EMAIL_CHASSIS_EVIDENCE", str(tmp_path / "evidence")))
    out.mkdir(parents=True, exist_ok=True)
    customers.login(page)
    page.get_by_role("link", name="Campañas", exact=True).click()
    page.get_by_role("button", name="Crear campaña", exact=True).click()
    page.get_by_label("Asunto", exact=True).fill("Chasis · ejemplo sintético")
    page.get_by_label("Título del mensaje", exact=True).fill("Un mensaje, varios diseños")
    page.get_by_label("Mensaje", exact=True).fill("El contenido se conserva al aplicar un chasis.")
    page.get_by_label("Condiciones y vigencia", exact=True).fill(
        "Prueba sintética, sin oferta real."
    )
    page.get_by_label("Diseño del correo", exact=True).select_option("protocol")
    page.locator(".audience-picker label").filter(has_text="persona0@example.test").get_by_role(
        "checkbox"
    ).check()
    page.get_by_text("Huesos y chasis", exact=True).click()
    page.get_by_label("Estilo base", exact=True).select_option("neutral")
    page.get_by_label("Ancho máximo · px", exact=True).fill("560")
    page.get_by_label("Tamaño del título · px", exact=True).fill("24")
    page.get_by_label("Tipografía del mensaje", exact=True).select_option("Georgia")
    page.get_by_label("Espacio interior del mensaje · px", exact=True).fill("24")
    page.get_by_label("Fondo del mensaje", exact=True).fill("#ffffff")
    page.get_by_label("Color del texto", exact=True).fill("#123456")
    page.get_by_label("Radio del botón · px", exact=True).fill("12")
    for width, label in [(1440, "desktop"), (390, "mobile")]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(
            path=str(out / ("editor-" + label + ".jpg")), type="jpeg", quality=75, full_page=True
        )
    with page.expect_download() as d:
        page.get_by_role("button", name="Exportar chasis", exact=True).click()
    exported = json.loads(Path(d.value.path()).read_text())
    assert exported["geometry"]["maxWidth"] == 560 and "content" not in exported
    assert "persona0" not in json.dumps(exported) and "Un mensaje" not in json.dumps(exported)
    page.get_by_role("button", name="Restablecer diseño", exact=True).click()
    assert page.get_by_label("Ancho máximo · px", exact=True).input_value() == ""
    page.get_by_label("Importar chasis · JSON", exact=True).set_input_files(
        {
            "name": "chassis.json",
            "mimeType": "application/json",
            "buffer": json.dumps(exported).encode(),
        }
    )
    playwright.expect(page.get_by_label("Ancho máximo · px", exact=True)).to_have_value("560")
    page.get_by_role("button", name="Guardar y revisar", exact=True).click()
    frame = page.frame_locator(".email-preview iframe")
    frame.get_by_role("heading", name="Un mensaje, varios diseños").wait_for()
    root = page.locator(".email-preview iframe").get_attribute("src").split("/email")[0]
    original = context.request.get(root).json()
    observations = []
    for family in ["classic", "barebone", "matte", "protocol", "arcane", "studio"]:
        page.get_by_label("Probar otro diseño", exact=True).select_option(family)
        frame.get_by_role("heading", name="Un mensaje, varios diseños").wait_for()
        page.wait_for_function(
            """name=>{
              const f=document.querySelector('.email-preview iframe').contentWindow;
              return f.location.search.includes('template_id='+name)||
                name==='protocol'&&!f.location.search;
            }""",
            arg=family,
        )
        for width in [1440, 390]:
            page.set_viewport_size({"width": width, "height": 1000})
            sample = frame.locator("html").evaluate("""e=>{
              const node=role=>e.querySelector('[data-101-bone-role='+role+']');
              const h=node('heading'),body=node('body');
              const content=node('content'),a=node('controls');
              const inset=content.querySelector(':scope > tbody > tr > td')||content;
              return {heading:getComputedStyle(h).fontSize,body:getComputedStyle(body).fontFamily,
                color:getComputedStyle(body).color,padding:getComputedStyle(inset).padding,
                radius:getComputedStyle(a).borderRadius,overflow:e.scrollWidth>innerWidth+1};
            }""")
            assert sample["heading"] == "24px" and sample["padding"] == "24px"
            assert "Georgia" in sample["body"] and sample["radius"] == "12px"
            assert sample["color"] == "rgb(18, 52, 86)" and not sample["overflow"]
            observations.append({"family": family, "width": width, **sample})
    page.get_by_label("Probar otro diseño", exact=True).select_option("protocol")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    page.get_by_role("button", name="Programar", exact=True).wait_for()
    assert context.request.get(root).json()["approved"]
    page.get_by_role("button", name="Editar", exact=True).click()
    page.get_by_text("Huesos y chasis", exact=True).click()
    page.get_by_label("Tamaño del título · px", exact=True).fill("28")
    page.get_by_role("button", name="Guardar y revisar", exact=True).click()
    page.get_by_role("button", name="Aprobar simulación", exact=True).wait_for()
    current = context.request.get(root).json()
    assert current["digest"] != original["digest"] and not current["approved"]
    assert current["document"]["content"] == original["document"]["content"]
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    page.get_by_role("button", name="Programar", exact=True).wait_for()
    assert context.request.get(root).json()["approved"]
    page.reload()
    frame.get_by_role("heading", name="Un mensaje, varios diseños").wait_for()
    assert frame.get_by_role("heading").evaluate("e=>getComputedStyle(e).fontSize") == "28px"
    assert not errors and not external and not csp
    (out / "checks.json").write_text(
        json.dumps(
            {
                "observations": observations,
                "export_import_roundtrip": True,
                "fresh_approval": True,
                "no_real_sends": True,
            },
            indent=2,
        )
    )
