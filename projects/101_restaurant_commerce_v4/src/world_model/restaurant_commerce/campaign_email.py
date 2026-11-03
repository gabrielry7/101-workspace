"""Email rendering is independent of transport; all human input is escaped."""
from html import escape
from urllib.parse import urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo
import re

VERSION = 'honorato-editorial-v1'


def render(document, recipient, ordering_url, unsubscribe_url):
    content = document['content']
    expiry = datetime.fromisoformat(document['expires_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M · Bogotá')
    name = recipient.get('name') or 'amigo de la casa'
    title, body, terms = (escape(content[k]) for k in ('title', 'body', 'terms'))
    label = 'DEMOSTRACIÓN · SIN ENVÍO REAL' if document['scope'] == 'test' else 'NOVEDADES DE LA CASA'
    brand = escape(document['brand']['name'])
    logo_path = document['brand'].get('logo_path')
    brand_html = f'<p style="font-size:32px;margin:16px 0">{brand}</p>'
    if logo_path and re.fullmatch(r'/assets/[a-z0-9-]+\.png', logo_path):
        origin = urlsplit(ordering_url)
        prefix = f'{origin.scheme}://{origin.netloc}' if origin.scheme in {'http','https'} else ''
        brand_html = f'<img src="{escape(prefix + logo_path, quote=True)}" width="280" alt="{brand}" style="display:block;width:100%;max-width:280px;height:auto;margin:24px 0">'

    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f4efe7;color:#27392d;font-family:Georgia,serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fffdf8;border:1px solid #ddd6c9"><tr><td style="padding:32px 28px;border-bottom:1px solid #ddd6c9"><p style="font:11px Arial,sans-serif;letter-spacing:2px">{label}</p>{brand_html}<p style="font:13px Arial,sans-serif">Una invitación a volver a la mesa.</p></td></tr>
<tr><td style="padding:32px 28px"><p>Hola, {escape(name)}.</p><h1 style="font-size:34px;line-height:1.15;font-weight:normal">{title}</h1><p style="font-size:18px;line-height:1.7;white-space:pre-line">{body}</p><p style="margin:32px 0"><a href="{escape(ordering_url, quote=True)}" style="display:inline-block;background:#27392d;color:#fffdf8;padding:16px 24px;font:bold 16px Arial,sans-serif;text-decoration:none">Ver la carta y pedir →</a></p><p style="font:13px/1.6 Arial,sans-serif">{terms}</p><p style="font:12px Arial,sans-serif">Vigencia: {escape(expiry)}</p></td></tr>
<tr><td style="padding:24px 28px;border-top:1px solid #ddd6c9;font:13px/1.6 Arial,sans-serif"><p>Recibes esta invitación por tu permiso de comunicaciones de {brand}.</p><a style="color:#27392d" href="{escape(unsubscribe_url, quote=True)}">Dejar de recibir promociones</a></td></tr></table></td></tr></table></body></html>'''
    text = f"{label}\n{document['brand']['name']}\nHola, {name}.\n\n{content['title']}\n\n{content['body']}\n\nVer la carta y pedir: {ordering_url}\n{content['terms']}\nVigencia: {expiry}\nDejar de recibir promociones: {unsubscribe_url}"
    return {'html': html, 'text': text, 'subject': content['subject']}
