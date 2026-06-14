"""
Production-ready F&O paper trading strategy.

Features:
- Defensive programming
- F&O lot-size aware quantity calculations
- Conservative momentum entries
- Stop loss, take profit, trailing stop
- Cooldown logic
- Drawdown protection
- Auto square-off
- Internal historical state
- Fault tolerant against corrupted snapshots
- No external dependencies
"""

from collections import deque
from datetime import datetime
from typing import Optional

from .config import (
    INITIAL_CAPITAL,
    MAX_CAPITAL_USAGE,
    MAX_DAILY_DRAWDOWN,
    MAX_CONSECUTIVE_LOSSES,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    TRAILING_STOP_PCT,
    COOLDOWN_SECONDS,
    AUTO_SQUARE_OFF_TIME,
    ENTRY_MOMENTUM,
    EXIT_MOMENTUM,
    MIN_OBSERVATIONS,
    MAX_HISTORY_SIZE,
)

# ============================================================
# Internal strategy state
# ============================================================

_STATE = {
    "prices": deque(maxlen=MAX_HISTORY_SIZE),
    "last_trade_time": None,
    "peak_equity": INITIAL_CAPITAL,
    "trading_disabled": False,
    "consecutive_losses": 0,
    "highest_price": None,
    "last_realized_pnl": 0.0,
}


# ============================================================
# Utilities
# ============================================================

def _hold(reason="No action"):
    return {
        "action": "HOLD",
        "symbol": "",
        "quantity": 0,
        "reason": reason[:250]
    }


def _safe_float(value) -> Optional[float]:
    try:
        if value is None:
            return None

        return float(value)
    except Exception:
        return None


def _safe_int(value, default=0):
    try:
        value = int(value)
        return max(value, 0)
    except Exception:
        return default


def _parse_time(snapshot):
    value = snapshot.get("time")

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _market_time_str(dt):
    if dt is None:
        return None

    return dt.strftime("%H:%M:%S")


def _extract_tradeable_symbol(snapshot):
    """
    Select first valid derivative instrument.
    """
    symbols = snapshot.get("symbols") or {}

    if not isinstance(symbols, dict):
        return None

    for symbol, data in symbols.items():
        if not isinstance(data, dict):
            continue

        ltp = _safe_float(data.get("ltp"))
        lot_size = _safe_int(data.get("lot_size"))

        if ltp is None:
            continue

        if lot_size <= 0:
            continue

        instrument_type = (
            str(data.get("instrument_type", ""))
            .upper()
            .strip()
        )

        if instrument_type not in ("OPTION", "FUTURE"):
            continue

        return {
            "symbol": symbol,
            "ltp": ltp,
            "lot_size": lot_size,
            "instrument_type": instrument_type,
        }

    return None


def _cooldown_active(now):
    last = _STATE["last_trade_time"]

    if last is None or now is None:
        return False

    seconds = (now - last).total_seconds()
    return seconds < COOLDOWN_SECONDS


def _record_trade(now):
    _STATE["last_trade_time"] = now


def _update_drawdown(equity):
    if equity is None:
        return

    peak = _STATE["peak_equity"]

    if equity > peak:
        _STATE["peak_equity"] = equity
        return

    drawdown = (
        peak - equity
    ) / max(peak, 1)

    if drawdown >= MAX_DAILY_DRAWDOWN:
        _STATE["trading_disabled"] = True


def _update_consecutive_losses(snapshot):
    realized = _safe_float(
        snapshot.get("realized_pnl")
    )

    if realized is None:
        return

    previous = _STATE["last_realized_pnl"]

    if realized < previous:
        _STATE["consecutive_losses"] += 1
    elif realized > previous:
        _STATE["consecutive_losses"] = 0

    _STATE["last_realized_pnl"] = realized

    if (
        _STATE["consecutive_losses"]
        >= MAX_CONSECUTIVE_LOSSES
    ):
        _STATE["trading_disabled"] = True


def _compute_quantity(cash, ltp, lot_size):
    """
    F&O position sizing.
    Always returns whole lots only.
    """

    cash = _safe_float(cash)
    ltp = _safe_float(ltp)

    if (
        cash is None
        or ltp is None
        or lot_size <= 0
        or ltp <= 0
    ):
        return 0

    usable_capital = cash * MAX_CAPITAL_USAGE

    one_lot_cost = ltp * lot_size

    if one_lot_cost <= 0:
        return 0

    lots = int(
        usable_capital //
        one_lot_cost
    )

    if lots <= 0:
        return 0

    quantity = lots * lot_size

    if quantity <= 0:
        return 0

    total_cost = quantity * ltp

    if total_cost > cash:
        return 0

    return quantity


# ============================================================
# Strategy
# ============================================================

def generate_signal(snapshot):
    """
    Returns:

    {
        "action":"BUY|SELL|HOLD",
        "symbol":"",
        "quantity":0,
        "reason":""
    }
    """

    try:
        if not isinstance(snapshot, dict):
            return _hold("Invalid snapshot")

        now = _parse_time(snapshot)

        equity = _safe_float(
            snapshot.get("equity")
        )

        _update_drawdown(equity)
        _update_consecutive_losses(snapshot)

        if _STATE["trading_disabled"]:
            return _hold(
                "Trading disabled by risk controls"
            )

        has_position = bool(
            snapshot.get("has_position")
        )

        # ====================================================
        # Position management
        # ====================================================

        if has_position:
            position = (
                snapshot.get("position")
                or {}
            )

            symbol = position.get("symbol")

            quantity = _safe_int(
                position.get("quantity")
            )

            entry_price = _safe_float(
                position.get("entry_price")
            )

            if (
                not symbol
                or quantity <= 0
                or entry_price is None
                or entry_price <= 0
            ):
                return _hold(
                    "Corrupted position"
                )

            market = (
                snapshot.get("symbols")
                or {}
            )

            data = market.get(symbol)

            if not isinstance(data, dict):
                return _hold(
                    "No market data"
                )

            current_price = _safe_float(
                data.get("ltp")
            )

            if (
                current_price is None
                or current_price <= 0
            ):
                return _hold(
                    "Invalid market price"
                )

            highest = _STATE["highest_price"]

            if (
                highest is None
                or current_price > highest
            ):
                highest = current_price
                _STATE["highest_price"] = highest

            pnl_pct = (
                current_price -
                entry_price
            ) / entry_price

            trailing_level = (
                highest *
                (1 - TRAILING_STOP_PCT)
            )

            time_str = _market_time_str(now)

            if (
                time_str
                and time_str >=
                AUTO_SQUARE_OFF_TIME
            ):
                _record_trade(now)

                return {
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "reason":
                        "Auto square-off"
                }

            if pnl_pct <= -STOP_LOSS_PCT:
                _record_trade(now)

                return {
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "reason":
                        "Stop loss"
                }

            if pnl_pct >= TAKE_PROFIT_PCT:
                _record_trade(now)

                return {
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "reason":
                        "Take profit"
                }

            if current_price < trailing_level:
                _record_trade(now)

                return {
                    "action": "SELL",
                    "symbol": symbol,
                    "quantity": quantity,
                    "reason":
                        "Trailing stop"
                }

            if (
                len(_STATE["prices"])
                >= MIN_OBSERVATIONS
            ):
                previous = (
                    _STATE["prices"][-1]
                )

                momentum = (
                    current_price -
                    previous
                ) / previous

                if momentum <= EXIT_MOMENTUM:
                    _record_trade(now)

                    return {
                        "action": "SELL",
                        "symbol": symbol,
                        "quantity": quantity,
                        "reason":
                            "Momentum reversal"
                    }

            return _hold(
                "Managing position"
            )

        # ====================================================
        # New entries
        # ====================================================

        _STATE["highest_price"] = None

        if _cooldown_active(now):
            return _hold(
                "Cooldown active"
            )

        instrument = (
            _extract_tradeable_symbol(
                snapshot
            )
        )

        if instrument is None:
            return _hold(
                "No derivative instrument"
            )

        ltp = instrument["ltp"]

        _STATE["prices"].append(ltp)

        if (
            len(_STATE["prices"])
            < MIN_OBSERVATIONS
        ):
            return _hold(
                "Building history"
            )

        reference = (
            _STATE["prices"][0]
        )

        if reference <= 0:
            return _hold(
                "Invalid history"
            )

        momentum = (
            ltp - reference
        ) / reference

        if momentum < ENTRY_MOMENTUM:
            return _hold(
                "Entry filter"
            )

        cash = _safe_float(
            snapshot.get("cash")
        )

        quantity = _compute_quantity(
            cash,
            ltp,
            instrument["lot_size"]
        )

        if quantity <= 0:
            return _hold(
                "Insufficient capital"
            )

        total_cost = quantity * ltp

        if (
            cash is None
            or total_cost > cash
        ):
            return _hold(
                "Cash validation failed"
            )

        _record_trade(now)

        return {
            "action": "BUY",
            "symbol":
                instrument["symbol"],
            "quantity":
                quantity,
            "reason":
                (
                    f"{instrument['instrument_type']} "
                    f"momentum breakout"
                )
        }

    except Exception:
        # Final fail-safe
        return _hold(
            "Internal strategy protection"
        )