"""Phone capture, real local rendering and exact-version export; fixture media only."""

# ruff: noqa: F401,F811 -- shared pytest fixtures
import json
import os
from datetime import date, timedelta
from pathlib import Path

from test_browser_security import browser, playwright
from test_combined_workspace_browser import site
from test_social_video import clips
from test_social_workspace_browser import (
    test_social_roundtrip_in_combined_dashboard as initial_static,
)


def video_review(page):
    review = page.get_by_role("region", name="Revisión de esta versión")
    details = review.locator(".review-assessment")
    if not details.evaluate("el=>el.open"):
        details.locator("summary").click()
    for label in (
        "Calidad técnica",
        "Exactitud de los datos",
        "Composición y claridad",
        "Estilo del negocio",
        "Cumple el propósito",
    ):
        review.get_by_label(label, exact=True).select_option("acceptable")
    review.get_by_label("Motivo de la decisión", exact=True).fill(
        "Secuencia sintética completa revisada, con sonido y encuadre de prueba."
    )
    assert review.get_by_role("button", name="Guardar revisión", exact=True).is_disabled()
    review.get_by_label("He visto y escuchado el vídeo completo", exact=False).check()
    review.get_by_role("button", name="Guardar revisión", exact=True).click()
    review.get_by_text("Última revisión: lista para aprobar", exact=True).wait_for()
    review.get_by_role("button", name="Aprobar esta versión", exact=True).click()
    review.get_by_role("button", name="Versión aprobada", exact=True).wait_for()


def test_phone_capture_preview_correction_approval_export(site, clips, tmp_path):
    initial_static(site, tmp_path)
    page, *_ = site
    out = Path(os.environ.get("SOCIAL_VIDEO_BROWSER_EVIDENCE", str(tmp_path / "video-evidence")))
    out.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "before-mobile.png"), full_page=True)
    panel = page.locator(".social-video")
    panel.locator("summary").first.click()
    panel.get_by_role("button", name="Crear guía de grabación", exact=True).click()
    panel.get_by_role("heading", name="El producto", exact=True).wait_for()
    panel.screenshot(path=str(out / "guide-empty-mobile.png"))
    permission = panel.get_by_text("Permiso del material", exact=True)
    permission.click()
    panel.get_by_label("Permiso para usar estas tomas", exact=True).fill(
        "Tomas sintéticas creadas y autorizadas para esta prueba, no son de Honorato."
    )
    panel.get_by_label("Revisar el permiso de las tomas", exact=True).fill(
        (date.today() + timedelta(days=7)).isoformat()
    )
    # Server receives the first chunk but its response is lost. Reselect resumes from its offset.
    intercepted = []

    def drop_response(route):
        if route.request.method == "PUT" and not intercepted:
            response = route.fetch()
            assert response.ok
            intercepted.append(route.request.url)
            route.abort()
        else:
            route.continue_()

    page.route("**/social/uploads/*", drop_response)
    panel.get_by_label("Subir toma: El producto", exact=True).set_input_files(str(clips[0]))
    panel.get_by_role("alert").wait_for()
    assert intercepted
    page.unroute("**/social/uploads/*", drop_response)
    panel.get_by_label("Subir toma: El producto", exact=True).set_input_files(str(clips[0]))
    try:
        panel.get_by_label("Toma elegida: El producto", exact=True).wait_for()
    except Exception:
        page.screenshot(path=str(out / "failure-upload.png"), full_page=True)
        raise AssertionError(panel.inner_text()) from None
    assert page.locator(".social-video").count() == 1
    for title, path in zip(("Un paso real", "El resultado"), clips[1:], strict=True):
        panel.get_by_label("Subir toma: " + title, exact=True).set_input_files(str(path))
        panel.get_by_label("Toma elegida: " + title, exact=True).wait_for()
    for title in ("El producto", "Un paso real", "El resultado"):
        panel.get_by_label("Hasta (s): " + title, exact=True).fill("1.5")
    panel.get_by_label("Encuadre horizontal: Un paso real", exact=True).fill("0.75")
    page.screenshot(path=str(out / "capture-mobile.png"), full_page=True)
    panel.get_by_role("button", name="Preparar montaje", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2", exact=True).wait_for(timeout=60000)
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.wait_for()
    video.evaluate("v=>v.play()")
    page.wait_for_function(
        "()=>document.querySelector('.video-preview')?.ended === true", timeout=20000
    )
    assert video.evaluate("v=>v.error===null && v.duration>4 && v.duration<5")
    video_review(page)
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar vídeo, portada", exact=False).click()
    download.value.save_as(str(out / "montage-v2.zip"))
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator(".video-finished").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "preview-desktop.png"), full_page=True)
    # Change just one cut; existing take selections/crops/audio survive.
    panel.get_by_label("Hasta (s): Un paso real", exact=True).fill("1.0")
    assert page.get_by_role("link", name="Descargar vídeo, portada", exact=False).count() == 0
    panel.get_by_role("button", name="Preparar montaje", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 3", exact=True).wait_for(timeout=60000)
    assert page.get_by_role("button", name="Versión aprobada", exact=True).count() == 0
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.evaluate("v=>v.play()")
    page.wait_for_function(
        "()=>document.querySelector('.video-preview')?.ended === true", timeout=20000
    )
    video_review(page)
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar vídeo, portada", exact=False).click()
    download.value.save_as(str(out / "montage-v3.zip"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator(".video-finished").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "preview-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    layout = panel.evaluate(
        "e=>({font:getComputedStyle(e).fontFamily,width:e.getBoundingClientRect().width,buttons:[...e.querySelectorAll('button')].map(b=>({text:b.textContent,height:b.getBoundingClientRect().height}))})"
    )
    assert "Inter" in layout["font"]
    assert all(b["height"] >= 44 for b in layout["buttons"])
    (out / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2))
