"""
Datetime utilities for the CMS backend.
Provides timezone-aware datetime functions.
"""
from datetime import datetime, timezone
from typing import Optional

import pytz


# Default timezone — overridden per-org when needed
_DEFAULT_TZ = "Asia/Ho_Chi_Minh"


def get_timezone(tz_name: Optional[str] = None):
    """
    Get timezone object.

    Args:
        tz_name: IANA timezone name. Defaults to system timezone.

    Returns:
        pytz timezone object
    """
    return pytz.timezone(tz_name or _DEFAULT_TZ)


def now(tz_name: Optional[str] = None) -> datetime:
    """
    Get current datetime in the specified timezone (aware, with tzinfo).
    Matches PostgreSQL TIMESTAMP WITH TIME ZONE columns.

    Args:
        tz_name: IANA timezone name. Defaults to system timezone.

    Returns:
        Current datetime with tzinfo
    """
    tz = get_timezone(tz_name)
    return datetime.now(tz)


def utcnow() -> datetime:
    """
    Get current UTC datetime (aware).

    Returns:
        Current UTC datetime with tzinfo
    """
    return datetime.now(timezone.utc)


def to_timezone(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """
    Convert datetime to specific timezone.

    Args:
        dt: Datetime to convert
        tz_name: Target timezone (default: system timezone)

    Returns:
        Datetime in target timezone
    """
    target_tz = get_timezone(tz_name)

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    return dt.astimezone(target_tz)


def to_org_timezone(dt: datetime, org_timezone: str) -> datetime:
    """
    Convert datetime to organization's timezone.

    Args:
        dt: Datetime to convert
        org_timezone: Organization's IANA timezone string

    Returns:
        Datetime in org timezone
    """
    return to_timezone(dt, org_timezone)
