# strategy.py

from collections import deque
from datetime import datetime

from .config import *

_STATE = {
    "nifty_history": deque(maxlen=MAX_HISTORY),
    "fast_ema": None,
    "slow_ema": None,
    "vwap_num": 0.0,
    "vwap_den": 0.0,
    "last_trade_time": None,
    "trades_today": 0,
    "current_date": None,
    "peak_equity": INITIAL_CAPITAL,
    "consecutive_losses": 0,
    "last_realized_pnl": 0.0,
    "highest_option_price": None,
    "trading_disabled": False,
}


def _hold(reason):
    return {
        "action": "HOLD",
        "symbol": "",
        "quantity": 0,
        "reason": reason[:250]
    }


def _safe_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _safe_int(v):
    try:
        return max(0, int(v))
    except Exception:
        return 0


def _parse_time(snapshot):
    value = snapshot.get("time")

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


def _time(dt):
    if dt is None:
        return None
    return dt.strftime("%H:%M:%S")


def _ema(previous, price, period):
    alpha = 2 / (period + 1)

    if previous is None:
        return price

    return previous + alpha * (price - previous)


def _rsi(prices):
    if len(prices) < RSI_PERIOD + 1:
        return None

    gains = []
    losses = []

    values = list(prices)

    for i in range(-RSI_PERIOD, 0):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / RSI_PERIOD
    avg_loss = sum(losses) / RSI_PERIOD

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def _cooldown(now):
    last = _STATE["last_trade_time"]

    if last is None or now is None:
        return False

    return (
        now - last
    ).total_seconds() < COOLDOWN_SECONDS


def _calculate_quantity(cash, premium):
    cash = _safe_float(cash)
    premium = _safe_float(premium)

    if (
        cash is None
        or premium is None
        or premium <= 0
    ):
        return 0

    usable = cash * MAX_CAPITAL_PER_TRADE

    one_lot_cost = premium * LOT_SIZE

    if one_lot_cost <= 0:
        return 0

    lots = int(usable // one_lot_cost)

    if lots <= 0:
        return 0

    return lots * LOT_SIZE


def generate_signal(snapshot):

    try:
        if not isinstance(snapshot, dict):
            return _hold("Invalid snapshot")

        now = _parse_time(snapshot)
        time_str = _time(now)

        nifty = _safe_float(snapshot.get("nifty"))

        if nifty is None or nifty <= 0:
            return _hold("Invalid NIFTY")

        # Daily reset
        if now:
            current_date = now.date()

            if _STATE["current_date"] != current_date:
                _STATE["current_date"] = current_date
                _STATE["trades_today"] = 0
                _STATE["consecutive_losses"] = 0
                _STATE["vwap_num"] = 0.0
                _STATE["vwap_den"] = 0.0
                _STATE["trading_disabled"] = False

        # Update indicators
        _STATE["nifty_history"].append(nifty)

        _STATE["fast_ema"] = _ema(
            _STATE["fast_ema"],
            nifty,
            FAST_EMA
        )

        _STATE["slow_ema"] = _ema(
            _STATE["slow_ema"],
            nifty,
            SLOW_EMA
        )

        _STATE["vwap_num"] += nifty
        _STATE["vwap_den"] += 1

        vwap = (
            _STATE["vwap_num"] /
            _STATE["vwap_den"]
        )

        rsi = _rsi(
            _STATE["nifty_history"]
        )

        # Analysis period
        if (
            time_str and
            ANALYSIS_START <= time_str < TRADING_START
        ):
            return _hold("Analysis period")

        # Trading hours over
        if (
            time_str and
            time_str >= AUTO_SQUARE_OFF
        ):
            return _hold("Market closed")

        # Risk controls
        equity = _safe_float(
            snapshot.get("equity")
        )

        if (
            equity and
            equity > _STATE["peak_equity"]
        ):
            _STATE["peak_equity"] = equity

        if equity:
            dd = (
                _STATE["peak_equity"] -
                equity
            ) / _STATE["peak_equity"]

            if dd >= MAX_DAILY_DRAWDOWN_PCT:
                _STATE["trading_disabled"] = True

        if _STATE["trading_disabled"]:
            return _hold("Drawdown lock")

        if (
            _STATE["trades_today"] >=
            MAX_TRADES_PER_DAY
        ):
            return _hold("Trade limit reached")

        # Position Management
        if snapshot.get("has_position"):

            position = snapshot.get(
                "position"
            ) or {}

            symbol = position.get(
                "symbol"
            )

            quantity = _safe_int(
                position.get(
                    "quantity"
                )
            )

            entry = _safe_float(
                position.get(
                    "entry_price"
                )
            )

            if (
                not symbol
                or quantity <= 0
                or entry is None
            ):
                return _hold(
                    "Corrupt position"
                )

            current = None

            if symbol == snapshot.get(
                "ce_symbol"
            ):
                current = _safe_float(
                    snapshot.get(
                        "ce_price"
                    )
                )

            elif symbol == snapshot.get(
                "pe_symbol"
            ):
                current = _safe_float(
                    snapshot.get(
                        "pe_price"
                    )
                )

            if current is None:
                return _hold(
                    "No option price"
                )

            highest = _STATE[
                "highest_option_price"
            ]

            if (
                highest is None
                or current > highest
            ):
                highest = current
                _STATE[
                    "highest_option_price"
                ] = highest

            pnl_pct = (
                current - entry
            ) / entry

            if pnl_pct <= -STOP_LOSS_PCT:
                action = "Stop Loss"

            elif pnl_pct >= TARGET_PCT:
                action = "Target"

            elif current <= (
                highest *
                (
                    1 -
                    TRAILING_STOP_PCT
                )
            ):
                action = "Trailing Stop"

            elif (
                time_str and
                time_str >=
                AUTO_SQUARE_OFF
            ):
                action = "Auto Square-Off"

            else:
                return _hold(
                    "Managing position"
                )

            _STATE[
                "last_trade_time"
            ] = now

            _STATE[
                "trades_today"
            ] += 1

            return {
                "action": "SELL",
                "symbol": symbol,
                "quantity": quantity,
                "reason": action
            }

        # No new entries
        if (
            time_str and
            time_str >=
            NO_NEW_ENTRY_AFTER
        ):
            return _hold(
                "Entry window closed"
            )

        if (
            time_str and
            LUNCH_START <=
            time_str <=
            LUNCH_END
        ):
            return _hold(
                "Lunch no-trade zone"
            )

        if _cooldown(now):
            return _hold(
                "Cooldown"
            )

        if (
            len(
                _STATE[
                    "nifty_history"
                ]
            ) <
            max(
                RSI_PERIOD,
                MOMENTUM_LOOKBACK
            )
        ):
            return _hold(
                "Building indicators"
            )

        fast = _STATE["fast_ema"]
        slow = _STATE["slow_ema"]

        if fast is None or slow is None:
            return _hold(
                "Indicators unavailable"
            )

        ema_sep = abs(
            fast - slow
        ) / nifty

        if (
            ema_sep <
            MIN_EMA_SEPARATION
        ):
            return _hold(
                "EMA compression"
            )

        momentum = (
            nifty -
            list(
                _STATE[
                    "nifty_history"
                ]
            )[
                -MOMENTUM_LOOKBACK
            ]
        ) / nifty

        if (
            abs(momentum) <
            MIN_MOMENTUM
        ):
            return _hold(
                "Low momentum"
            )

        if (
            rsi is None
        ):
            return _hold(
                "RSI unavailable"
            )

        if (
            NO_TRADE_RSI_LOW <=
            rsi <=
            NO_TRADE_RSI_HIGH
        ):
            return _hold(
                "RSI no-trade zone"
            )

        symbol = ""
        premium = None
        reason = ""

        # Bullish
        if (
            fast > slow and
            nifty > vwap and
            RSI_BULL_MIN <
            rsi <
            RSI_BULL_MAX and
            momentum >
            MIN_MOMENTUM
        ):

            symbol = snapshot.get(
                "ce_symbol"
            )

            premium = _safe_float(
                snapshot.get(
                    "ce_price"
                )
            )

            reason = (
                "Bullish multi-factor"
            )

        # Bearish
        elif (
            fast < slow and
            nifty < vwap and
            RSI_BEAR_MIN <
            rsi <
            RSI_BEAR_MAX and
            momentum <
            -MIN_MOMENTUM
        ):

            symbol = snapshot.get(
                "pe_symbol"
            )

            premium = _safe_float(
                snapshot.get(
                    "pe_price"
                )
            )

            reason = (
                "Bearish multi-factor"
            )

        else:
            return _hold(
                "No high-confidence setup"
            )

        if (
            not symbol
            or premium is None
            or premium <= 0
        ):
            return _hold(
                "Invalid ATM option"
            )

        quantity = _calculate_quantity(
            snapshot.get("cash"),
            premium
        )

        if quantity <= 0:
            return _hold(
                "Insufficient cash"
            )

        _STATE[
            "highest_option_price"
        ] = premium

        _STATE[
            "last_trade_time"
        ] = now

        _STATE[
            "trades_today"
        ] += 1

        return {
            "action": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "reason": reason
        }

    except Exception:
        return _hold(
            "Internal protection"
        )