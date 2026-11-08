"""One-page export of a saved report; no database/provider reads."""

from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


def money(value, currency):
    if value is None:
        return "—"
    number = (
        f"{value if currency == 'COP' else value / 100:,.0f}"
        if currency == "COP"
        else f"{value / 100:,.2f}"
    )
    return currency + " " + number.replace(",", "_").replace(".", ",").replace("_", ".")


def render(d):
    font = Path(__file__).parent / "web" / "report-inter.ttf"
    if "ReportInter" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ReportInter", str(font)))
    out = BytesIO()
    c = Canvas(out, pagesize=A4)
    width, height = A4
    c.setTitle(d["business_name"] + " " + d["month"])
    y = height - 40

    def text(value, size=10, gap=8):
        nonlocal y
        p = Paragraph(
            escape(str(value)),
            ParagraphStyle("r", fontName="ReportInter", fontSize=size, leading=size * 1.3),
        )
        _, h = p.wrap(width - 80, 1000)
        p.drawOn(c, 40, y - h)
        y -= h + gap

    text(d["business_name"], 20)
    text("Informe mensual | " + d["month"] + " | Comparación: " + d["comparison"], 12)
    text(d["currency"] + " | " + d["timezone"])
    for label, key, is_money in [
        ("Ventas en línea", "net", True),
        ("Pedidos pagados", "paid_orders", False),
        ("Valor promedio por pedido", "average", True),
    ]:
        a, b = [v["sales"][key] for v in d["periods"]]
        fmt = lambda v: money(v, d["currency"]) if is_money else ("—" if v is None else str(v))
        text(label + ": " + fmt(a) + "     Anterior: " + fmt(b), 12)
    a = d["periods"][0]["sales"]
    text(
        "Cobrado: "
        + money(a["captured"], d["currency"])
        + "    Devoluciones: "
        + money(a["refunds"], d["currency"])
    )
    text("Campañas", 13)
    for label, key in [("Envíos aceptados", "accepted"), ("Visitas registradas", "visits")]:
        text(
            label
            + ": "
            + str(
                d["periods"][0]["activity"][key]
                if d["periods"][0]["activity"][key] is not None
                else "—"
            )
            + " / Anterior: "
            + str(
                d["periods"][1]["activity"][key]
                if d["periods"][1]["activity"][key] is not None
                else "—"
            ),
            9,
            4,
        )
    if not d["campaigns"]:
        text("Sin ventas atribuidas registradas.")
    for r in d["campaigns"]:
        text(
            r["name"][:75]
            + ": "
            + money(r["current"]["net"], d["currency"])
            + " / "
            + money(r["previous"]["net"], d["currency"])
            + " | Pedidos: "
            + str(r["current"]["paid_orders"] if r["current"]["paid_orders"] is not None else "—")
            + " / "
            + str(
                r["previous"]["paid_orders"] if r["previous"]["paid_orders"] is not None else "—"
            ),
            9,
            5,
        )
    text("Sitio web", 13)
    for label, key in [
        ("Visitantes", "visitors"),
        ("Visitas", "visits"),
        ("Páginas vistas", "pageviews"),
    ]:
        a, b = [v["website"].get("values", {}).get(key) for v in d["periods"]]
        text(
            label
            + ": "
            + ("—" if a is None else str(a))
            + "     Anterior: "
            + ("—" if b is None else str(b)),
            10,
            4,
        )
    notes = list(
        dict.fromkeys(
            d["gaps"]
            + [p["sales"]["note"] for p in d["periods"]]
            + [
                p["month"] + ": " + p["website"]["note"]
                for p in d["periods"]
                if p["website"].get("note")
            ]
        )
    )
    for note in notes:
        text(note, 8, 4)
    text("Actualizado: " + d["generated_at"][:19].replace("T", " ") + " UTC", 8)
    if y < 30:
        raise ValueError("Monthly PDF exceeds one page")
    c.showPage()
    c.save()
    return out.getvalue()
