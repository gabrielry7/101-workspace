"""Normal 101 campaign editor -> style comparison -> new approval, no real delivery."""

# ruff: noqa: F401,F811
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import test_customer_workspace_browser as customers
from test_browser_security import browser, playwright
from test_workspace_views_browser import site


def test_campaign_templates_in_shared_workspace_desktop_phone(site, tmp_path):
    page, context, url, app, errors, external, csp = site
    out = Path(os.environ.get("EMAIL_BROWSER_EVIDENCE", str(tmp_path / "email-evidence")))
    out.mkdir(parents=True, exist_ok=True)
    customers.login(page)
    page.get_by_role("link", name="Campañas", exact=True).click()
    page.get_by_role("button", name="Crear campaña", exact=True).click()
    page.get_by_label("Asunto", exact=True).fill("Una nota para ti · prueba")
    page.get_by_label("Título del mensaje", exact=True).fill("Nos vemos en la mesa")
    page.get_by_label("Mensaje", exact=True).fill(
        "Mensaje de demostración con información confirmada.\n\n"
        "Cada diseño usa exactamente este mismo contenido."
    )
    page.get_by_label("Condiciones y vigencia", exact=True).fill(
        "Prueba sintética. No representa una oferta de Honorato."
    )
    page.get_by_label("Diseño del correo", exact=True).select_option("matte")
    form_measure = page.get_by_label("Diseño del correo", exact=True).evaluate(
        "e=>({height:e.getBoundingClientRect().height,font:getComputedStyle(e).fontFamily})"
    )
    assert form_measure["height"] >= 44 and "Inter" in form_measure["font"]
    page.locator(".audience-picker label").filter(has_text="persona0@example.test").get_by_role(
        "checkbox"
    ).check()
    page.screenshot(path=str(out / "editor-desktop.png"), full_page=True)
    page.get_by_role("button", name="Guardar y revisar", exact=True).click()
    frame = page.frame_locator(".email-preview iframe")
    frame.get_by_role("heading", name="Nos vemos en la mesa", exact=True).wait_for()
    cid = parse_qs(urlsplit(page.url).query)["campaign"][0]
    root = "/api/operator/restaurants/honorato-demo/campaigns/" + cid
    # Resolve the normal business-scoped API from the actual iframe URL.
    root = page.locator(".email-preview iframe").get_attribute("src").split("/email")[0]
    original = context.request.get(root).json()
    assert original["document"]["email_design"]["template_id"] == "matte"
    page.get_by_role("checkbox").check()
    for name in ["barebone", "matte", "protocol", "arcane", "studio", "classic"]:
        page.get_by_label("Probar otro diseño", exact=True).select_option(name)
        frame.get_by_role("heading", name="Nos vemos en la mesa", exact=True).wait_for()
        if name != "matte":
            page.wait_for_function(
                "name=>document.querySelector('.email-preview iframe')"
                ".contentWindow.location.search.includes('template_id='+name)",
                arg=name,
            )
            assert page.get_by_role("button", name="Aprobar simulación", exact=True).is_disabled()
            assert not page.get_by_role("checkbox").is_checked()
        frame.locator("body").evaluate("()=>document.fonts.ready")
        for size, label in [
            ({"width": 1440, "height": 1000}, "desktop"),
            ({"width": 390, "height": 844}, "mobile"),
        ]:
            page.set_viewport_size(size)
            preview = context.new_page()
            preview.set_viewport_size(size)
            preview.goto(page.locator(".email-preview iframe").get_attribute("src"))
            preview.evaluate("document.fonts.ready")
            preview.screenshot(path=str(out / (name + "-" + label + ".png")), full_page=True)
            preview.close()
            assert frame.locator("html").evaluate("e=>e.scrollWidth<=innerWidth+1")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        now = context.request.get(root).json()
        assert (
            now["digest"] == original["digest"]
            and now["document"]["content"] == original["document"]["content"]
        )
    page.get_by_label("Probar otro diseño", exact=True).select_option("protocol")
    page.get_by_role("button", name="Guardar este diseño", exact=True).click()
    page.get_by_text("Diseño guardado en una nueva versión.", exact=False).wait_for()
    current = context.request.get(root).json()
    assert current["digest"] != original["digest"] and not current["approved"]
    assert current["document"]["content"] == original["document"]["content"]
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Aprobar simulación", exact=True).click()
    page.get_by_role("button", name="Programar", exact=True).wait_for(state="visible")
    assert context.request.get(root).json()["approved"]
    page.get_by_label("Probar otro diseño", exact=True).select_option("arcane")
    assert page.get_by_role("button", name="Programar", exact=True).is_disabled()
    page.get_by_label("Probar otro diseño", exact=True).select_option("protocol")
    assert page.get_by_role("button", name="Programar", exact=True).is_enabled()
    page.reload()
    frame.get_by_role("heading", name="Nos vemos en la mesa", exact=True).wait_for()
    assert page.get_by_label("Probar otro diseño", exact=True).input_value() == "protocol"
    for size, label in [
        ({"width": 1440, "height": 1000}, "desktop"),
        ({"width": 390, "height": 844}, "mobile"),
    ]:
        page.set_viewport_size(size)
        page.screenshot(path=str(out / ("workspace-" + label + ".png")), full_page=True)
    measure = page.get_by_label("Probar otro diseño", exact=True).evaluate(
        "e=>({height:e.getBoundingClientRect().height,font:getComputedStyle(e).fontFamily})"
    )
    assert measure["height"] >= 44 and "Inter" in measure["font"]
    assert not errors and not external and not csp
    (out / "checks.json").write_text(
        json.dumps(
            {
                "font_controls": measure,
                "form_controls": form_measure,
                "all_six_designs": True,
                "readonly_comparison": True,
                "fresh_approval": True,
                "mobile_desktop_overflow": False,
                "actual_runtime": "isolated normal app; synthetic fixture content",
            },
            indent=2,
        )
    )
