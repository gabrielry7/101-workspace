from __future__ import annotations

from urllib.parse import quote

from .schemas import OrderOut, ReservationOut


def _money(minor: int, currency: str) -> str:
    if currency == "COP":
        return f"${minor:,.0f} COP"
    return f"{minor} {currency}"


def format_order_message(order: OrderOut) -> str:
    lines = [
        f"Nuevo pedido #{order.public_code}",
        f"Estado: {order.status}",
        "",
    ]
    for item in order.items:
        lines.append(f"{item.quantity} × {item.name} — {_money(item.line_total_minor, order.currency)}")
        for modifier in item.modifiers:
            lines.append(f"  • {modifier.group_name}: {modifier.option_name}")
    lines += [
        "",
        f"Total: {_money(order.total_minor, order.currency)}",
        f"Cliente: {order.customer_name or 'Cliente'} · {order.customer_phone}",
        "Recogida en el local",
    ]
    if order.notes:
        lines.append(f"Nota: {order.notes}")
    return "\n".join(lines)


def format_reservation_message(reservation: ReservationOut) -> str:
    return "\n".join(
        [
            f"Nueva reserva #{reservation.public_code}",
            f"{reservation.starts_at.isoformat()} · {reservation.party_size} personas",
            f"Cliente: {reservation.customer_name or 'Cliente'} · {reservation.customer_phone}",
            f"Nota: {reservation.notes}" if reservation.notes else "",
        ]
    ).strip()


def whatsapp_click_to_chat_url(phone_e164: str, message: str) -> str:
    clean = "".join(ch for ch in phone_e164 if ch.isdigit())
    return f"https://wa.me/{clean}?text={quote(message)}"
