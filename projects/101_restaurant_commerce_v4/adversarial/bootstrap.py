"""Fetch only the pinned local fault proxy; scanner/browser runners bootstrap their tools."""

import hashlib
import json
import os
import urllib.request
from pathlib import Path

root = Path(os.environ.get("COMMERCE_TOOLCHAIN", "/tmp/101-commerce-toolchain"))
path = root / "toxiproxy-server"
url = "https://github.com/Shopify/toxiproxy/releases/download/v2.13.0/toxiproxy-server-linux-amd64"
expected = "bf529e8bb9a05cd293f45a3f1d0aa66ff9469680dcdca7e0ebeae21f1b83de89"
if not path.exists():
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("Toxiproxy download checksum mismatch")
    path.write_bytes(data)
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise RuntimeError("Existing Toxiproxy checksum mismatch")
path.chmod(0o755)
(root / "toxiproxy-download.json").write_text(
    json.dumps({"release": "v2.13.0", "url": url, "sha256": expected})
)
