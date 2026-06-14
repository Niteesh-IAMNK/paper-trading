from datetime import datetime, timezone
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


def utc_now():
    """
    Returns current UTC datetime.
    """
    return datetime.now(UTC)


def ist_now():
    """
    Returns current IST datetime.
    """
    return datetime.now(IST)


def to_utc(dt):
    """
    Convert datetime to UTC.
    """

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=IST
        )

    return dt.astimezone(UTC)


def to_ist(dt):
    """
    Convert datetime to IST.
    """

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=UTC
        )

    return dt.astimezone(IST)


def utc_iso():
    """
    Current UTC ISO string.
    """

    return utc_now().isoformat()


def ist_iso():
    """
    Current IST ISO string.
    """

    return ist_now().isoformat()


def market_date():
    """
    Returns market date in IST.
    """

    return ist_now().strftime(
        "%Y-%m-%d"
    )


def market_time():
    """
    Returns market time in IST.
    """

    return ist_now().strftime(
        "%H:%M:%S"
    )