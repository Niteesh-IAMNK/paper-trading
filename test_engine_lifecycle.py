"""Unit tests for engine scheduler and lot sizing."""

from datetime import datetime
from zoneinfo import ZoneInfo

from shared.config import LOT_SIZE, DEFAULT_LOTS
from shared.engine_scheduler import (
    SESSION_ANALYSIS,
    SESSION_BEFORE_MARKET,
    SESSION_DAILY_SUMMARY,
    SESSION_SHUTDOWN,
    SESSION_SQUARE_OFF,
    SESSION_TRADING,
    compute_sleep_seconds,
    get_session,
    should_fetch_market_data,
)
from shared.lot_sizing import (
    format_lot_log,
    is_valid_lot_quantity,
    lots_to_quantity,
    resolve_lots_from_signal,
    validate_buy_quantity,
)

IST = ZoneInfo("Asia/Kolkata")


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2026, 7, 2, hour, minute, tzinfo=IST)


def test_session_before_market():
    assert get_session(_dt(8, 15)) == SESSION_BEFORE_MARKET


def test_session_analysis():
    assert get_session(_dt(9, 20)) == SESSION_ANALYSIS


def test_session_trading():
    assert get_session(_dt(11, 0)) == SESSION_TRADING


def test_session_square_off():
    assert get_session(_dt(15, 25)) == SESSION_SQUARE_OFF


def test_session_daily_summary():
    assert get_session(_dt(15, 30)) == SESSION_DAILY_SUMMARY


def test_session_shutdown():
    assert get_session(_dt(16, 0)) == SESSION_SHUTDOWN


def test_sleep_before_market_from_early_start():
    seconds = compute_sleep_seconds(
        SESSION_BEFORE_MARKET,
        _dt(8, 15),
    )
    assert 2400 < seconds <= 2700


def test_should_not_fetch_before_market():
    assert should_fetch_market_data(SESSION_BEFORE_MARKET) is False


def test_default_lots_when_missing():
    assert resolve_lots_from_signal({"action": "BUY"}) == DEFAULT_LOTS


def test_explicit_lots():
    assert resolve_lots_from_signal({"lots": 3}) == 3


def test_lot_quantity_conversion():
    assert lots_to_quantity(1) == LOT_SIZE
    assert lots_to_quantity(3) == LOT_SIZE * 3


def test_validate_lot_quantity():
    assert is_valid_lot_quantity(65) is True
    assert is_valid_lot_quantity(25) is False
    valid, _ = validate_buy_quantity(65)
    assert valid is True
    valid, message = validate_buy_quantity(25)
    assert valid is False
    assert "multiple" in message


def test_format_lot_log():
    assert "1 lot" in format_lot_log(1, 65)
    assert "3 lots" in format_lot_log(3, 195)


if __name__ == "__main__":
    tests = [
        test_session_before_market,
        test_session_analysis,
        test_session_trading,
        test_session_square_off,
        test_session_daily_summary,
        test_session_shutdown,
        test_sleep_before_market_from_early_start,
        test_should_not_fetch_before_market,
        test_default_lots_when_missing,
        test_explicit_lots,
        test_lot_quantity_conversion,
        test_validate_lot_quantity,
        test_format_lot_log,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print("All infrastructure unit tests passed.")
