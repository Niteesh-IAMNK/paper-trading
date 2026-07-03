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

_MARKET_OPEN = MARKET_OPEN[:5]
_ANALYSIS_END = ANALYSIS_END[:5]
_TRADING_STOP = TRADING_STOP[:5]
_MARKET_CLOSE = MARKET_CLOSE[:5]


def current_time():
    return datetime.now(IST).strftime("%H:%M")


def is_market_open():
    """Market is open 09:15 – 15:30 IST."""
    now = current_time()
    return _MARKET_OPEN <= now < _MARKET_CLOSE


def is_analysis_time():
    now = current_time()
    return _MARKET_OPEN <= now < _ANALYSIS_END


def is_trading_time():
    """Active trading ends at 15:20 (10 minutes before market close)."""
    now = current_time()
    return _ANALYSIS_END <= now < _TRADING_STOP


def is_square_off_time():
    """Square-off window: 15:20 – 15:30 (market close)."""
    now = current_time()
    return _TRADING_STOP <= now < _MARKET_CLOSE
