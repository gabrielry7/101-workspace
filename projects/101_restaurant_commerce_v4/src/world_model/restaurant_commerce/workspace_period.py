"""One inclusive Bogotá calendar-period contract for dashboard drill-through."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException

ZONE = ZoneInfo("America/Bogota")


def period(date_from=None, date_to=None, *, default=False):
    if not date_from and not date_to:
        if not default:
            return None
        end = datetime.now(ZONE).date()
        start = end - timedelta(days=6)
    else:
        try:
            start = date.fromisoformat(date_from or "")
            end = date.fromisoformat(date_to or "")
        except ValueError:
            raise HTTPException(422, "Fechas inválidas") from None
    if end == date.max or end < start or (end - start).days > 365:
        raise HTTPException(422, "Elige hasta 366 días, en orden")
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "start": datetime.combine(start, time.min, ZONE).astimezone(timezone.utc),
        "end": datetime.combine(end + timedelta(days=1), time.min, ZONE).astimezone(
            timezone.utc
        ),
    }


def clauses(column, selected):
    return [column >= selected["start"], column < selected["end"]] if selected else []
