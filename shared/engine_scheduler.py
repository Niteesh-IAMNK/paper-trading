"""
Trading day session scheduler.

Schedule (IST):
    09:15  market open
    10:30  trading begins (after analysis)
    15:20  trading stops — square-off begins
    15:30  market close — daily summary, then shutdown
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from shared.config import (
    ANALYSIS_END,
    MARKET_CLOSE,
    MARKET_OPEN,
    TIMEZONE,
    TRADING_STOP,
)

IST = ZoneInfo(TIMEZONE)

SESSION_BEFORE_MARKET = "before_market"
SESSION_ANALYSIS = "analysis"
SESSION_TRADING = "trading"
SESSION_SQUARE_OFF = "square_off"
SESSION_DAILY_SUMMARY = "daily_summary"
SESSION_SHUTDOWN = "shutdown"

PRE_MARKET_WAKE = "09:00"

# Derived HH:MM boundaries (single source: shared/config.py)
MARKET_OPEN_HM = MARKET_OPEN[:5]
ANALYSIS_END_HM = ANALYSIS_END[:5]
TRADING_STOP_HM = TRADING_STOP[:5]      # 15:20 — stop trading
MARKET_CLOSE_HM = MARKET_CLOSE[:5]      # 15:30 — market close
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

    if current < MARKET_OPEN_HM:
        return SESSION_BEFORE_MARKET
    if current < ANALYSIS_END_HM:
        return SESSION_ANALYSIS
    if current < TRADING_STOP_HM:
        return SESSION_TRADING
    if current < MARKET_CLOSE_HM:
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
    Square-off (15:20–15:30): poll until market close summary.
    """
    current = dt or _now()
    clock = _time_str(current)

    if session == SESSION_BEFORE_MARKET:
        if clock < PRE_MARKET_WAKE:
            return seconds_until(PRE_MARKET_WAKE, current)
        return seconds_until(MARKET_OPEN_HM, current)

    if session in {SESSION_DAILY_SUMMARY, SESSION_SQUARE_OFF}:
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
    }
