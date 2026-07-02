"""
Trading day session scheduler.

Sessions (IST):
    before_market → analysis → trading → square_off → daily_summary → shutdown
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from shared.config import TIMEZONE

IST = ZoneInfo(TIMEZONE)

SESSION_BEFORE_MARKET = "before_market"
SESSION_ANALYSIS = "analysis"
SESSION_TRADING = "trading"
SESSION_SQUARE_OFF = "square_off"
SESSION_DAILY_SUMMARY = "daily_summary"
SESSION_SHUTDOWN = "shutdown"

# Session boundaries (HH:MM, IST)
PRE_MARKET_WAKE = "09:00"
MARKET_OPEN = "09:15"
TRADING_START = "10:30"
SQUARE_OFF_START = "15:20"
SUMMARY_START = "15:30"
SUMMARY_END = "15:31"

ACTIVE_LOOP_SLEEP_SECONDS = 2.0
PRE_SUMMARY_SLEEP_SECONDS = 1.0


def _now() -> datetime:
    return datetime.now(IST)


def _time_str(dt: datetime | None = None) -> str:
    current = dt or _now()
    return current.strftime("%H:%M")


def get_session(dt: datetime | None = None) -> str:
    """Return the current trading-day session."""
    current = _time_str(dt)

    if current < MARKET_OPEN:
        return SESSION_BEFORE_MARKET
    if current < TRADING_START:
        return SESSION_ANALYSIS
    if current < SQUARE_OFF_START:
        return SESSION_TRADING
    if current < SUMMARY_START:
        return SESSION_SQUARE_OFF
    if current < SUMMARY_END:
        return SESSION_DAILY_SUMMARY
    return SESSION_SHUTDOWN


def _parse_hm(value: str, reference: datetime) -> datetime:
    hour, minute = map(int, value.split(":"))
    return reference.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def seconds_until(target: str, dt: datetime | None = None) -> float:
    """Seconds until the next HH:MM boundary today (minimum 1 second)."""
    current = dt or _now()
    target_dt = _parse_hm(target, current)

    if target_dt <= current:
        return ACTIVE_LOOP_SLEEP_SECONDS

    return max(1.0, (target_dt - current).total_seconds())


def compute_sleep_seconds(session: str, dt: datetime | None = None) -> float:
    """
    Sleep efficiently until the next required event.

    Before market: sleep until 09:00, then until 09:15.
    Active sessions: short polling interval.
    After square-off: poll until daily summary window.
    """
    current = dt or _now()
    clock = _time_str(current)

    if session == SESSION_BEFORE_MARKET:
        if clock < PRE_MARKET_WAKE:
            return seconds_until(PRE_MARKET_WAKE, current)
        return seconds_until(MARKET_OPEN, current)

    if session == SESSION_DAILY_SUMMARY:
        return PRE_SUMMARY_SLEEP_SECONDS

    if session == SESSION_SQUARE_OFF:
        return PRE_SUMMARY_SLEEP_SECONDS

    if session == SESSION_SHUTDOWN:
        return 0.0

    return ACTIVE_LOOP_SLEEP_SECONDS


def is_past_trading_day(dt: datetime | None = None) -> bool:
    """True when the daily summary window has passed."""
    return get_session(dt) == SESSION_SHUTDOWN


def should_fetch_market_data(session: str) -> bool:
    """Only call FYERS during active market sessions."""
    return session in {
        SESSION_ANALYSIS,
        SESSION_TRADING,
        SESSION_SQUARE_OFF,
        SESSION_DAILY_SUMMARY,
    }
