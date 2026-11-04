"""Bind retained ZAP reviews to exact findings and their current rendering owners."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from gate import finding


def zap_finding(alert, base, root):
    evidence = {
        k: alert.get(k) for k in ["alertRef", "name", "risk", "confidence", "param", "evidence"]
    }
    # JSON-stored payloads require reviewing the actual consumer, not just MIME labels.
    if str(alert.get("pluginId")) == "40014":
        evidence["owners"] = {
            name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
            for name in [
                "src/world_model/restaurant_commerce/api.py",
                "src/world_model/restaurant_commerce/growth.py",
                "src/world_model/restaurant_commerce/web/growth.js",
                "src/world_model/restaurant_commerce/web/shared.js",
            ]
        }
    return finding(
        alert.get("alertRef", alert["pluginId"]),
        alert["url"].removeprefix(base),
        json.dumps(evidence, sort_keys=True),
        alert["risk"].upper(),
        "zap",
    )


def reviewed_alerts(alerts, base, root):
    reviews = json.loads((Path(root) / "security/reviews.json").read_text())["reviews"]
    accepted = []
    blocked = []
    for alert in alerts:
        item = zap_finding(alert, base, root)
        matches = [
            r
            for r in reviews
            if all(
                r.get(k) == item[k] for k in ["layer", "rule", "path", "severity", "fingerprint"]
            )
            and r.get("owner")
            and r.get("reason")
            and datetime.fromisoformat(r["expires_at"].replace("Z", "+00:00")) > datetime.now(UTC)
        ]
        (accepted if item["severity"] == "INFORMATIONAL" or len(matches) == 1 else blocked).append(
            item
        )
    return {"accepted": accepted, "blocked": blocked, "outcome": "FAIL" if blocked else "PASS"}
