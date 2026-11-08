"""Outer access boundary for the temporary, isolated social demonstration.

This is not production authentication. Normal workspace sessions/CSRF remain
required after the gate. The same gate protects direct tunnel access.
"""
import base64
import hmac
import json
from pathlib import Path

from starlette.responses import PlainTextResponse, RedirectResponse


class PreviewAccess:
    def __init__(self, app, access_file):
        self.app = app
        path = Path(access_file)
        if path.stat().st_mode & 0o077:
            raise ValueError("Preview access file must be private (0600)")
        credentials = json.loads(path.read_text())
        password = credentials["password"]
        if len(password) < 24 or not password.isascii():
            raise ValueError("Use a generated preview password of at least 24 characters")
        self.authorization = ("Basic " + base64.b64encode(
            ("101:" + password).encode()).decode()).encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if not hmac.compare_digest(headers.get(b"authorization", b""), self.authorization):
            return await PlainTextResponse("Vista previa privada de 101", status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="101 preview", charset="UTF-8"',
                         "Cache-Control": "no-store"})(scope, receive, send)
        if scope["path"] == "/":
            return await RedirectResponse("/workspace/social", status_code=302)(scope, receive, send)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                outgoing = []
                for name, value in message.get("headers", []):
                    if name.lower() in {b"cache-control", b"x-robots-tag", b"referrer-policy"}:
                        continue
                    if name.lower() == b"set-cookie" and b"secure" not in value.lower():
                        value += b"; Secure"
                    outgoing.append((name, value))
                outgoing.extend([(b"cache-control", b"no-store"),
                                 (b"x-robots-tag", b"noindex, nofollow"),
                                 (b"referrer-policy", b"no-referrer")])
                message = {**message, "headers": outgoing}
            await send(message)
        await self.app(scope, receive, secure_send)
