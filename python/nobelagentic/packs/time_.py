"""time pack."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..tools import tool


@tool
def now(tz: str = "UTC") -> str:
    """Current date and time in an IANA timezone, e.g. 'Africa/Lagos'."""
    return datetime.now(ZoneInfo(tz)).isoformat()


@tool
def date_add(date: str, days: int = 0, hours: int = 0) -> str:
    """Add days/hours to an ISO date string."""
    return (datetime.fromisoformat(date) + timedelta(days=days, hours=hours)).isoformat()


@tool
def convert_timezone(datetime_iso: str, to_tz: str) -> str:
    """Convert an ISO datetime to another timezone."""
    d = datetime.fromisoformat(datetime_iso)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(ZoneInfo(to_tz)).isoformat()


TOOLS = [now, date_add, convert_timezone]
