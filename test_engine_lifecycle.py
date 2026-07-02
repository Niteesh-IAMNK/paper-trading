"""Production infrastructure unit tests."""

from datetime import datetime
from zoneinfo import ZoneInfo

from shared.config import DEFAULT_LOTS, LOT_SIZE
from shared.engine_scheduler import (
    SESSION_ANALYSIS,
    SESSION_BEFORE_MARKET,
    SESSION_SHUTDOWN,
    SESSION_SQUARE_OFF,
    SESSION_TRADING,
    compute_sleep_seconds,
    get_session,
    should_fetch_market_data,
)
from shared.lot_sizing import (
    format_lot_log,
    lots_to_quantity,
    resolve_lots_from_signal,
    validate_buy_quantity,
)
from shared.signal_adapter import prepare_execution_signal, resolve_trade_symbol

IST = ZoneInfo("Asia/Kolkata")


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2026, 7, 2, hour, minute, tzinfo=IST)


def test_centralized_lot_size():
    assert LOT_SIZE == 65
    assert lots_to_quantity(1) == 65
    assert lots_to_quantity(3) == 195


def test_default_lots_when_strategy_omits_lots():
    assert resolve_lots_from_signal({"action": "BUY"}) == DEFAULT_LOTS


def test_explicit_lots_from_strategy():
    assert resolve_lots_from_signal({"lots": 5}) == 5


def test_legacy_quantity_converted_to_lots():
    assert resolve_lots_from_signal({"quantity": 130}) == 2


def test_gpt_option_type_resolves_to_symbol():
    snapshot = {
        "ce_symbol": "NSE:CE",
        "pe_symbol": "NSE:PE",
    }
    signal = {"action": "BUY", "option_type": "CE", "lots": 2}
    prepared = prepare_execution_signal(signal, snapshot)
    assert prepared["symbol"] == "NSE:CE"
    assert prepared["lots"] == 2
    assert prepared["quantity"] == 130


def test_gemini_style_signal():
    snapshot = {"ce_symbol": "NSE:CE", "pe_symbol": "NSE:PE"}
    signal = {
        "action": "BUY",
        "symbol": "NSE:CE",
        "lots": 3,
        "reason": "test",
    }
    prepared = prepare_execution_signal(signal, snapshot)
    assert prepared["quantity"] == 195


def test_schedule_trading_stops_at_1520():
    assert get_session(_dt(15, 19)) == SESSION_TRADING
    assert get_session(_dt(15, 20)) == SESSION_SQUARE_OFF


def test_schedule_market_close_at_1530():
    assert get_session(_dt(15, 29)) == SESSION_SQUARE_OFF
    assert get_session(_dt(15, 31)) == SESSION_SHUTDOWN


def test_no_market_fetch_before_open():
    assert should_fetch_market_data(SESSION_BEFORE_MARKET) is False


def test_pre_market_sleep_is_efficient():
    seconds = compute_sleep_seconds(SESSION_BEFORE_MARKET, _dt(8, 15))
    assert seconds > 2400


def test_lot_log_format():
    text = format_lot_log(3, 195)
    assert "3 lots" in text
    assert "195" in text


if __name__ == "__main__":
    tests = [
        test_centralized_lot_size,
        test_default_lots_when_strategy_omits_lots,
        test_explicit_lots_from_strategy,
        test_legacy_quantity_converted_to_lots,
        test_gpt_option_type_resolves_to_symbol,
        test_gemini_style_signal,
        test_schedule_trading_stops_at_1520,
        test_schedule_market_close_at_1530,
        test_no_market_fetch_before_open,
        test_pre_market_sleep_is_efficient,
        test_lot_log_format,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print("All production infrastructure tests passed.")
