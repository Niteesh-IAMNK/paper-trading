from collections import deque
from datetime import datetime

from .config import *


_STATE = {
    "date": None,
    "nifty": deque(maxlen=MAX_HISTORY),
    "ce": deque(maxlen=MAX_HISTORY),
    "pe": deque(maxlen=MAX_HISTORY),
    "volume": deque(maxlen=MAX_HISTORY),
    "fast_ema": None,
    "mid_ema": None,
    "slow_ema": None,
    "ce_ema": None,
    "pe_ema": None,
    "vwap_num": 0.0,
    "vwap_den": 0.0,
    "day_open": None,
}


def _hold(reason):
    return {
        "action": "HOLD",
        "reason": reason[:250],
    }


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _date_from_snapshot(snapshot):
    value = snapshot.get("date") or snapshot.get("trading_day") or snapshot.get("time")
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except Exception:
        return None


def _reset_if_new_day(snapshot):
    current_date = _date_from_snapshot(snapshot)
    if current_date is None or current_date == _STATE["date"]:
        return

    _STATE["date"] = current_date
    _STATE["nifty"].clear()
    _STATE["ce"].clear()
    _STATE["pe"].clear()
    _STATE["volume"].clear()
    _STATE["fast_ema"] = None
    _STATE["mid_ema"] = None
    _STATE["slow_ema"] = None
    _STATE["ce_ema"] = None
    _STATE["pe_ema"] = None
    _STATE["vwap_num"] = 0.0
    _STATE["vwap_den"] = 0.0
    _STATE["day_open"] = None


def _ema(previous, price, period):
    alpha = 2 / (period + 1)
    if previous is None:
        return price
    return previous + alpha * (price - previous)


def _pct_change(values, lookback):
    if len(values) <= lookback:
        return None
    old = values[-lookback - 1]
    new = values[-1]
    if old <= 0:
        return None
    return (new - old) / old


def _rsi(values):
    if len(values) < RSI_PERIOD + 1:
        return None

    data = list(values)
    gains = 0.0
    losses = 0.0
    for index in range(-RSI_PERIOD, 0):
        change = data[index] - data[index - 1]
        if change >= 0:
            gains += change
        else:
            losses += abs(change)

    if losses == 0:
        return 100.0

    rs = gains / losses
    return 100 - (100 / (1 + rs))


def _atr_pct(values):
    if len(values) < ATR_PERIOD + 1:
        return None

    data = list(values)
    start = len(data) - ATR_PERIOD
    ranges = [abs(data[index] - data[index - 1]) for index in range(start, len(data))]
    price = data[-1]
    if price <= 0:
        return None
    return (sum(ranges) / ATR_PERIOD) / price


def _trend_efficiency(values, lookback):
    if len(values) <= lookback:
        return 0.0

    data = list(values)[-lookback - 1:]
    direct_move = abs(data[-1] - data[0])
    travelled = sum(abs(data[index] - data[index - 1]) for index in range(1, len(data)))
    if travelled <= 0:
        return 0.0
    return direct_move / travelled


def _vwap():
    if _STATE["vwap_den"] <= 0:
        return None
    return _STATE["vwap_num"] / _STATE["vwap_den"]


def _update_indicators(snapshot, nifty, ce_price, pe_price):
    volume = (
        _safe_float(snapshot.get("volume"))
        or _safe_float(snapshot.get("nifty_volume"))
        or 1.0
    )
    volume = max(volume, 1.0)

    if _STATE["day_open"] is None:
        _STATE["day_open"] = nifty

    _STATE["nifty"].append(nifty)
    _STATE["volume"].append(volume)
    _STATE["vwap_num"] += nifty * volume
    _STATE["vwap_den"] += volume
    _STATE["fast_ema"] = _ema(_STATE["fast_ema"], nifty, FAST_EMA)
    _STATE["mid_ema"] = _ema(_STATE["mid_ema"], nifty, MID_EMA)
    _STATE["slow_ema"] = _ema(_STATE["slow_ema"], nifty, SLOW_EMA)

    if ce_price is not None and ce_price > 0:
        _STATE["ce"].append(ce_price)
        _STATE["ce_ema"] = _ema(_STATE["ce_ema"], ce_price, FAST_EMA)

    if pe_price is not None and pe_price > 0:
        _STATE["pe"].append(pe_price)
        _STATE["pe_ema"] = _ema(_STATE["pe_ema"], pe_price, FAST_EMA)


def _option_confirmed(direction, premium, option_history, option_ema):
    if premium is None or premium < OPTION_MIN_PREMIUM:
        return False

    option_momentum = _pct_change(option_history, OPTION_MOMENTUM_LOOKBACK)
    if option_momentum is None:
        return False

    if option_momentum < OPTION_CONFIRMATION_MOVE:
        return False

    if option_ema is not None and premium < option_ema:
        return False

    return direction in ("CE", "PE")


def _score_direction(direction, nifty, vwap, rsi, atr, momentum):
    fast = _STATE["fast_ema"]
    mid = _STATE["mid_ema"]
    slow = _STATE["slow_ema"]
    if None in (fast, mid, slow, vwap, rsi, atr, momentum):
        return 0.0

    history = _STATE["nifty"]
    recent = list(history)[-BREAKOUT_LOOKBACK - 1:-1]
    if not recent:
        return 0.0

    spread = abs(fast - slow) / nifty
    efficiency = _trend_efficiency(history, BREAKOUT_LOOKBACK)
    day_move = (nifty - (_STATE["day_open"] or nifty)) / nifty

    if direction == "CE":
        score = 0.0
        score += 0.95 if fast > mid > slow else 0.0
        score += 0.55 if nifty > vwap else 0.0
        score += 0.55 if nifty > max(recent) else 0.0
        score += 0.35 if momentum > MIN_ABS_MOMENTUM else 0.0
        score += 0.30 if 52 <= rsi <= 79 else 0.0
        score += min(0.55, max(0.0, day_move * 90))
    else:
        score = 0.0
        score += 0.95 if fast < mid < slow else 0.0
        score += 0.55 if nifty < vwap else 0.0
        score += 0.55 if nifty < min(recent) else 0.0
        score += 0.35 if momentum < -MIN_ABS_MOMENTUM else 0.0
        score += 0.30 if 21 <= rsi <= 48 else 0.0
        score += min(0.55, max(0.0, -day_move * 90))

    score += min(0.60, efficiency)
    score += min(0.45, spread / max(MIN_EMA_SPREAD, 0.0001) * 0.12)
    score += 0.30 if MIN_ATR_PCT <= atr <= MAX_ATR_PCT else -0.55
    return score


def _edge_multiplier(score):
    if score >= 4.35:
        return EXTREME_EDGE_MULTIPLIER
    if score >= 3.85:
        return HIGH_EDGE_MULTIPLIER
    if score >= 3.35:
        return MEDIUM_EDGE_MULTIPLIER
    return 1.0


def _equity_scale(snapshot):
    equity = (
        _safe_float(snapshot.get("equity"))
        or _safe_float(snapshot.get("portfolio_value"))
        or _safe_float(snapshot.get("capital"))
        or REFERENCE_EQUITY
    )
    if equity <= 0:
        return 1.0
    return max(0.25, equity / REFERENCE_EQUITY)


def _lots_for_score(snapshot, score, atr):
    scale = _equity_scale(snapshot)
    volatility_adjustment = 1.0

    if atr is not None:
        if atr > 0.0045:
            volatility_adjustment = 0.55
        elif atr > 0.0032:
            volatility_adjustment = 0.75
        elif atr < 0.00035:
            volatility_adjustment = 0.70

    raw_lots = BASE_LOTS * scale * _edge_multiplier(score) * volatility_adjustment
    lots = int(round(raw_lots))
    return max(1, min(MAX_LOTS, lots))


def _buy_signal(direction, lots, confidence, reason):
    return {
        "action": "BUY",
        "option_type": direction,
        "lots": lots,
        "confidence": round(confidence, 2),
        "reason": reason[:250],
    }


def generate_signal(snapshot):
    try:
        if not isinstance(snapshot, dict):
            return _hold("Invalid snapshot")

        nifty = _safe_float(snapshot.get("nifty"))
        if nifty is None or nifty <= 0:
            return _hold("Invalid NIFTY")

        _reset_if_new_day(snapshot)

        ce_price = _safe_float(snapshot.get("ce_price"))
        pe_price = _safe_float(snapshot.get("pe_price"))
        _update_indicators(snapshot, nifty, ce_price, pe_price)

        enough_history = max(SLOW_EMA, BREAKOUT_LOOKBACK, RSI_PERIOD, ATR_PERIOD) + 2
        if len(_STATE["nifty"]) < enough_history:
            return _hold("Building signal history")

        vwap = _vwap()
        rsi = _rsi(_STATE["nifty"])
        atr = _atr_pct(_STATE["nifty"])
        momentum = _pct_change(_STATE["nifty"], MOMENTUM_LOOKBACK)

        if None in (vwap, rsi, atr, momentum):
            return _hold("Indicators unavailable")
        if atr < MIN_ATR_PCT:
            return _hold("Insufficient realized movement")
        if atr > MAX_ATR_PCT:
            return _hold("Chaotic volatility")
        if abs(momentum) < MIN_ABS_MOMENTUM:
            return _hold("No directional pressure")

        ce_score = _score_direction("CE", nifty, vwap, rsi, atr, momentum)
        pe_score = _score_direction("PE", nifty, vwap, rsi, atr, momentum)

        ce_ok = _option_confirmed("CE", ce_price, _STATE["ce"], _STATE["ce_ema"])
        pe_ok = _option_confirmed("PE", pe_price, _STATE["pe"], _STATE["pe_ema"])

        candidates = []
        if ce_ok and ce_score >= MIN_EDGE_SCORE:
            candidates.append(("CE", ce_score))
        if pe_ok and pe_score >= MIN_EDGE_SCORE:
            candidates.append(("PE", pe_score))

        if not candidates:
            return _hold("No confirmed directional edge")

        direction, score = max(candidates, key=lambda item: item[1])
        lots = _lots_for_score(snapshot, score, atr)
        confidence = min(99.0, max(50.0, 50.0 + (score - MIN_EDGE_SCORE) * 18.0))
        reason = (
            f"{direction} trend expansion | score {score:.2f} | "
            f"rsi {rsi:.1f} | momentum {momentum:.2%} | atr {atr:.2%}"
        )
        return _buy_signal(direction, lots, confidence, reason)

    except Exception:
        return _hold("Internal strategy protection")
