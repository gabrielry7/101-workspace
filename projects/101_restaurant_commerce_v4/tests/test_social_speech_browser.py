"""Normal desktop/phone speech-correction workflow; fake recognizer, real renders."""

# ruff: noqa: F401,F811
import json
import os
from datetime import date, timedelta
from pathlib import Path

from test_browser_security import browser, playwright
from test_combined_workspace_browser import site
from test_social_speech import FakeSpeech
from test_social_video import clips
from test_social_video_browser import video_review
from test_social_workspace_browser import (
    test_social_roundtrip_in_combined_dashboard as initial_static,
)


def test_spoken_capture_word_revision_and_export(site, clips, tmp_path):
    page, _, _, app, *_ = site
    fake = FakeSpeech()
    fake.authorize = lambda business: True  # Explicitly synthetic browser app only.
    app.state.social_transcriber = fake
    initial_static(site, tmp_path)
    out = Path(os.environ.get("SOCIAL_SPEECH_BROWSER_EVIDENCE", str(tmp_path / "speech-browser")))
    out.mkdir(parents=True, exist_ok=True)
    panel = page.locator(".social-video")
    panel.locator("summary").first.click()
    page.set_viewport_size({"width": 1440, "height": 1000})
    panel.screenshot(path=str(out / "before-desktop.png"))
    panel.get_by_label("Tipo de vídeo", exact=True).select_option("spoken_answer")
    panel.get_by_role("button", name="Crear guía de grabación", exact=True).click()
    panel.get_by_role("heading", name="Tu respuesta", exact=True).wait_for()
    panel.get_by_text("Permiso del material", exact=True).click()
    panel.get_by_label("Permiso para usar estas tomas", exact=True).fill(
        "Material sintético autorizado para la prueba; no es de un cliente."
    )
    panel.get_by_label("Revisar el permiso de las tomas", exact=True).fill(
        (date.today() + timedelta(days=5)).isoformat()
    )
    for title, path in zip(("El producto", "Tu respuesta", "El resultado"), clips, strict=True):
        panel.get_by_label("Subir toma: " + title, exact=True).set_input_files(str(path))
        panel.get_by_label("Toma elegida: " + title, exact=True).wait_for()
        panel.get_by_label("Hasta (s): " + title, exact=True).fill("2")
    speech = page.get_by_role("region", name="Transcripción y subtítulos")
    speech.get_by_role("button", name="Transcribir respuesta en español", exact=True).click()
    speech.get_by_label("Palabra 3", exact=True).wait_for(timeout=30000)
    assert fake.calls == 1
    assert speech.get_by_label("Palabra 3", exact=True).input_value() == "panes."
    speech.get_by_label("Revisé las palabras", exact=False).check()
    panel.get_by_role("button", name="Preparar vídeo con subtítulos", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 2", exact=True).wait_for(timeout=60000)
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.evaluate("v=>v.play()")
    page.wait_for_function("()=>document.querySelector('.video-preview')?.ended", timeout=20000)
    video_review(page)
    page.set_viewport_size({"width": 390, "height": 844})
    speech.scroll_into_view_if_needed()
    page.screenshot(path=str(out / "before-correction-mobile.png"), full_page=True)
    speech.get_by_label("Palabra 3", exact=True).fill("pasteles.")
    assert page.get_by_role("link", name="Descargar vídeo, portada", exact=False).count() == 0
    speech.get_by_label("Revisé las palabras", exact=False).check()
    speech.get_by_role("button", name="Guardar correcciones de palabras", exact=True).click()
    speech.get_by_text("Texto automático sin verificar · revisión 1.", exact=False).wait_for()
    panel.get_by_role("button", name="Preparar vídeo con subtítulos", exact=True).click()
    page.get_by_role("heading", name="Revisa la versión 3", exact=True).wait_for(timeout=60000)
    assert fake.calls == 1
    video = page.get_by_label("Vista previa del montaje", exact=True)
    video.evaluate("v=>v.play()")
    page.wait_for_function("()=>document.querySelector('.video-preview')?.ended", timeout=20000)
    video_review(page)
    with page.expect_download() as download:
        page.get_by_role("link", name="Descargar vídeo, portada", exact=False).click()
    download.value.save_as(str(out / "spoken-corrected.zip"))
    speech.scroll_into_view_if_needed()
    page.screenshot(path=str(out / "corrected-mobile.png"), full_page=True)
    speech.screenshot(path=str(out / "editor-mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.set_viewport_size({"width": 1440, "height": 1000})
    speech.scroll_into_view_if_needed()
    page.screenshot(path=str(out / "corrected-desktop.png"), full_page=True)
    speech.screenshot(path=str(out / "editor-desktop.png"))
    layout = speech.evaluate(
        "e=>({font:getComputedStyle(e).fontFamily,buttons:[...e.querySelectorAll('button,input,select')].map(b=>({text:b.textContent,height:(b.type==='checkbox'?b.closest('label'):b).getBoundingClientRect().height}))})"
    )
    assert layout["buttons"]
    assert "Inter" in layout["font"] and all(b["height"] >= 44 for b in layout["buttons"])
    (out / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2))
