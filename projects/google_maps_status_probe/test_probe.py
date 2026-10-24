from maps_status_probe import classify_body_text

def test_permanently_closed_english():
    assert classify_body_text("lepimp bar Permanently closed Directions Save", True) == "CLOSED_PERMANENTLY"

def test_permanently_closed_spanish():
    assert classify_body_text("lepimp bar Cerrado permanentemente Indicaciones Guardar", True) == "CLOSED_PERMANENTLY"

def test_open_requires_panel():
    assert classify_body_text("Random search results", False) == "UNKNOWN"
    assert classify_body_text("Business Directions Save", True) == "OPEN_OR_UNMARKED"

def test_blocked():
    assert classify_body_text("Our systems have detected unusual traffic", False) == "BLOCKED"
