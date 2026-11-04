"""Authorize only the escaped email renderer's exact inline styles in previews."""

import base64
import hashlib
from html.parser import HTMLParser


class _Styles(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hashes = set()

    def handle_starttag(self, _tag, attrs):
        for name, value in attrs:
            if name == "style" and value is not None:
                digest = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
                self.hashes.add("'sha256-" + digest + "'")


def preview_csp(rendered_html):
    # This consumes trusted renderer output, never arbitrary submitted HTML.
    styles = _Styles()
    styles.feed(rendered_html)
    allowed = "'unsafe-hashes' " + " ".join(sorted(styles.hashes)) if styles.hashes else "'none'"
    return (
        "default-src 'none'; img-src 'self'; style-src "
        + allowed
        + "; frame-ancestors 'self'; base-uri 'none'; form-action 'none'; sandbox allow-same-origin"
    )
