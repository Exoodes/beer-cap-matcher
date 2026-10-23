"""Dates in the collection's own time zone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Prague")


def today_local() -> date:
    """Today in Prague, whatever time zone the server runs in."""
    return datetime.now(LOCAL_TZ).date()
