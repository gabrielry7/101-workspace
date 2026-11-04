"""Move trusted email styles into a nonce-authorized preview stylesheet.

The transport email stays unchanged. This only transforms escaped renderer output,
never raw submitted HTML; scripts and inline style attributes remain prohibited.
"""

import secrets
from html import escape
from html.parser import HTMLParser


class _Preview(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.styles = {}
        self.parts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        style = values.pop("style", None)
        if style is not None:
            name = self.styles.setdefault(style, f"preview-style-{len(self.styles)}")
            values["class"] = ((values.get("class") or "") + " " + name).strip()
        rendered = "".join(
            " " + key + ("" if value is None else '="' + escape(value, quote=True) + '"')
            for key, value in values.items()
        )
        self.parts.append("<" + tag + rendered + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append("</" + tag + ">")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append("&" + name + ";")

    def handle_charref(self, name):
        self.parts.append("&#" + name + ";")

    def handle_decl(self, decl):
        self.parts.append("<!" + decl + ">")

    def handle_comment(self, data):
        self.parts.append("<!--" + data + "-->")


def secure_preview(rendered_html):
    parser = _Preview()
    parser.feed(rendered_html)
    parser.close()
    nonce = secrets.token_urlsafe(24)
    # Style values originate in the trusted renderer. Escape angle brackets as
    # CSS escapes as well, so a future value cannot terminate this style element.
    rules = "\n".join(
        "." + name + "{" + value.replace("<", "\\3c ").replace(">", "\\3e ") + "}"
        for value, name in parser.styles.items()
    )
    sheet = '<style nonce="' + nonce + '">' + rules + "</style>"
    markup = "".join(parser.parts)
    markup = (
        markup.replace("</head>", sheet + "</head>", 1) if "</head>" in markup else sheet + markup
    )
    policy = (
        "default-src 'none'; img-src 'self'; style-src 'nonce-"
        + nonce
        + "'; style-src-attr 'none'; frame-ancestors 'self'; base-uri 'none'; "
        "form-action 'none'; sandbox allow-same-origin"
    )
    return markup, policy
