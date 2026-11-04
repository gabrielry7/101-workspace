"""Stored JSON alerts need exact, current consumer review, never a global waiver."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "security"))
from alert_review import reviewed_alerts, zap_finding


def test_json_review_expires_and_changes_with_rendering_owner(tmp_path):
    names = ["api.py", "growth.py", "web/growth.js", "web/shared.js"]
    for name in names:
        p = tmp_path / "src/world_model/restaurant_commerce" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("synthetic owner")
    (tmp_path / "security").mkdir()
    reviews = tmp_path / "security/reviews.json"
    alert = {
        "pluginId": "40014",
        "alertRef": "40014",
        "url": "http://127.0.0.1:123/api/rewards",
        "name": "Stored JSON",
        "risk": "Low",
        "confidence": "Low",
        "param": "name",
        "evidence": "",
    }
    item = zap_finding(alert, "http://127.0.0.1:123", tmp_path)
    review = {
        **item,
        "owner": "test",
        "reason": "verified text consumer",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    reviews.write_text(json.dumps({"reviews": [review]}))
    assert reviewed_alerts([alert], "http://127.0.0.1:123", tmp_path)["outcome"] == "PASS"
    review["expires_at"] = "2000-01-01T00:00:00Z"
    reviews.write_text(json.dumps({"reviews": [review]}))
    assert reviewed_alerts([alert], "http://127.0.0.1:123", tmp_path)["outcome"] == "FAIL"
    review["expires_at"] = "2099-01-01T00:00:00Z"
    reviews.write_text(json.dumps({"reviews": [review]}))
    (tmp_path / "src/world_model/restaurant_commerce/web/growth.js").write_text("changed renderer")
    assert reviewed_alerts([alert], "http://127.0.0.1:123", tmp_path)["outcome"] == "FAIL"
