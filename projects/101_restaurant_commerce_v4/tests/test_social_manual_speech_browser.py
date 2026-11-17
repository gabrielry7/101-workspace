"""Owner can subtitle real uploaded media while recognition is unavailable."""

# ruff: noqa: F401,F811
import json
import os
from datetime import date, timedelta
from pathlib import Path

from test_browser_security import browser, playwright
from test_combined_workspace_browser import site
from test_social_video import clips
from test_social_video_browser import video_review
from test_social_workspace_browser import (
    test_social_roundtrip_in_combined_dashboard as initial_static,
)


def test_manual_subtitles_without_worker_phone_correction_and_export(site, clips, tmp_path):
    page, _, _, app, *_ = site
    app.state.social_transcriber = None
    initial_static(site, tmp_path)
    out = Path(os.environ.get("SOCIAL_MANUAL_BROWSER_EVIDENCE", str(tmp_path / "manual-subtitles")))
    out.mkdir(parents=True, exist_ok=True)
    panel = page.locator(".social-video")
    panel.locator("summary").first.click()
    page.set_viewport_size({"width": 390, "height": 844})
    panel.get_by_label("Tipo de vídeo", exact=True).select_option("spoken_answer")
    panel.get_by_role("button", name="Crear guía de grabación", exact=True).click()
    panel.get_by_role("heading", name="Tu respuesta", exact=True).wait_for()
    panel.get_by_text("Permiso del material", exact=True).click()
    panel.get_by_label("Permiso para usar estas tomas", exact=True).fill(
        "Material sintético de prueba; no corresponde a Honorato "
        "ni representa palabras reconocidas."
    )
    panel.get_by_label("Revisar el permiso de las tomas", exact=True).fill(
        (date.today() + timedelta(days=5)).isoformat()
    )
    for title, path in zip(("El producto", "Tu respuesta", "El resultado"), clips, strict=True):
        panel.get_by_label("Subir toma: " + title, exact=True).set_input_files(str(path))
        panel.get_by_label("Toma elegida: " + title, exact=True).wait_for()
        panel.get_by_label("Hasta (s): " + title, exact=True).fill("2")
    speech = page.get_by_role("region", name="Transcripción y subtítulos")
    assert speech.get_by_role(
        "button", name="Transcribir respuesta en español", exact=True
    ).is_disabled()
    speech.screenshot(path=str(out / "before-manual-mobile.png"))
    speech.get_by_text("Escribir subtítulos con sus tiempos", exact=True).click()
    speech.screenshot(path=str(out / "intake-mobile.png"))
    speech.get_by_label("Texto del subtítulo 1", exact=True).fill("No vendemos panes.")
    speech.get_by_label("Desde (s), subtítulo 1", exact=True).fill("0.2")
    speech.get_by_label("Hasta (s), subtítulo 1", exact=True).fill("1.8")
    speech.get_by_label("Escuché la toma completa", exact=False).check()
    speech.get_by_role("button", name="Guardar subtítulos manuales", exact=True).click()
    speech.get_by_label("Fragmento 1", exact=True).wait_for()
    speech.get_by_text("Subtítulos escritos por el negocio", exact=False).wait_for()
    speech.get_by_label("Revisé las palabras", exact=False).check()
    panel.get_by_role("button", name="Preparar vídeo con subtítulos", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2", exact=True).wait_for(timeout=60000)
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.evaluate("v=>v.play()")
    page.wait_for_function("()=>document.querySelector('.video-preview')?.ended", timeout=20000)
    video_review(page)
    speech.get_by_label("Fragmento 1", exact=True).fill("No vendemos pasteles.")
    speech.get_by_label("Desde (s), fragmento 1", exact=True).fill("0.3")
    assert page.get_by_role("link", name="Descargar vídeo, portada", exact=False).count() == 0
    speech.get_by_label("Revisé las palabras", exact=False).check()
    speech.get_by_role("button", name="Guardar correcciones de subtítulos", exact=True).click()
    speech.get_by_text("revisión 1.", exact=False).wait_for()
    panel.get_by_role("button", name="Preparar vídeo con subtítulos", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 3", exact=True).wait_for(timeout=60000)
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.evaluate("v=>v.play()")
    page.wait_for_function("()=>document.querySelector('.video-preview')?.ended", timeout=20000)
    video_review(page)
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar vídeo, portada", exact=False).click()
    download.value.save_as(str(out / "manual-corrected.zip"))
    for name, size in [
        ("mobile", {"width": 390, "height": 844}),
        ("desktop", {"width": 1440, "height": 1000}),
    ]:
        page.set_viewport_size(size)
        speech.scroll_into_view_if_needed()
        speech.screenshot(path=str(out / (name + ".png")))
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    measures = speech.evaluate(
        "e=>({font:getComputedStyle(e).fontFamily,controls:[...e.querySelectorAll('input,select,button')].map(x=>({height:(x.type==='checkbox'?x.closest('label'):x).getBoundingClientRect().height}))})"
    )
    assert "Inter" in measures["font"] and measures["controls"]
    assert all(x["height"] >= 44 for x in measures["controls"])
    (out / "layout.json").write_text(json.dumps(measures, indent=2))
