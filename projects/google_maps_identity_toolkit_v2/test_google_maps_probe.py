from google_maps_probe import classify_body_text, build_place_id_url


def test_permanently_closed_english():
    assert classify_body_text("lepimp bar Permanently closed Directions Save", True) == "CLOSED_PERMANENTLY"


def test_permanently_closed_spanish():
    assert classify_body_text("lepimp Cerrado permanentemente Indicaciones Guardar", True) == "CLOSED_PERMANENTLY"


def test_open_requires_panel():
    assert classify_body_text("Random search results", False) == "UNKNOWN"
    assert classify_body_text("Business Directions Save", True) == "OPEN_OR_UNMARKED"


def test_blocked():
    assert classify_body_text("Our systems have detected unusual traffic", False) == "BLOCKED"


def test_place_id_url():
    assert "place_id:ChIJabc" in build_place_id_url("ChIJabc")
