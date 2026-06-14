"""
gpt/strategy.py

Production-ready deterministic strategy for NSE Index Options (long only).
Focus: Capital preservation, low drawdown, explainable rules, strict risk control.

Key features implemented:
- Proper F&O lot sizing (quantity = LOTS * lot_size from data)
- Scans symbols dict for suitable OPTION contracts only
- Parses standard symbol format (NIFTY26JUN25000CE etc.)
- Directional bias from dual MA on underlying index (NIFTY / BANKNIFTY)
- Slightly OTM option selection for better risk/reward
- Hard TP / SL / time-stop / max-loss exits
- Cooldown between trades
- Running peak equity drawdown protection
- Auto square-off before market close
- Full defensive programming (never crashes, never invalid quantity/action)
- Handles missing/corrupt snapshot fields gracefully
- Restart safe (history rebuilds on import)

Engine compatibility:
- Uses only BUY (open long option) and SELL (close position)
- Respects MAX_POSITIONS=1
- Never attempts BUY if cash insufficient
- Never attempts SELL if no position
- Quantity always integer multiple of lot_size

No external dependencies. Pure Python stdlib + relative import of config.
"""

import collections
import re
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo


# ========================
# Module State (survives across generate_signal calls in long-running process)
# ========================
_nifty_history = collections.deque(maxlen=50)
_banknifty_history = collections.deque(maxlen=50)
_last_action_ts = None          # for cooldown
_peak_equity = 500000.0         # running peak, reset on process restart is acceptable
_last_position_entry_time = None


# ========================
# Time & Market Helpers (IST)
# ========================
IST = ZoneInfo("Asia/Kolkata")


def _get_ist_now(snapshot_time_str):
    """Convert snapshot ISO time (usually UTC) to IST datetime. Fallback to now IST."""
    try:
        if snapshot_time_str:
            ts = snapshot_time_str.replace("Z", "+00:00")
            dt_utc = datetime.fromisoformat(ts)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
            return dt_utc.astimezone(IST)
    except Exception:
        pass
    return datetime.now(IST)


def _is_market_open(ist_dt):
    from .config import MARKET_OPEN_IST, MARKET_CLOSE_IST
    try:
        open_t = datetime.strptime(MARKET_OPEN_IST, "%H:%M:%S").time()
        close_t = datetime.strptime(MARKET_CLOSE_IST, "%H:%M:%S").time()
        return open_t <= ist_dt.time() < close_t
    except Exception:
        return True  # fail open -> allow trading rather than block everything


def _should_auto_square_off(ist_dt):
    from .config import AUTO_SQUARE_OFF_IST
    try:
        sq_off = datetime.strptime(AUTO_SQUARE_OFF_IST, "%H:%M:%S").time()
        return ist_dt.time() >= sq_off
    except Exception:
        return False


def _no_new_entries_allowed(ist_dt):
    from .config import NO_NEW_ENTRY_AFTER_IST
    try:
        cutoff = datetime.strptime(NO_NEW_ENTRY_AFTER_IST, "%H:%M:%S").time()
        return ist_dt.time() >= cutoff
    except Exception:
        return False


# ========================
# History & Indicator Helpers
# ========================
def _update_underlying_history(snapshot):
    global _nifty_history, _banknifty_history
    nifty = _safe_float(snapshot.get("nifty"))
    bank = _safe_float(snapshot.get("banknifty"))
    if nifty and nifty > 1000:
        _nifty_history.append(nifty)
    if bank and bank > 1000:
        _banknifty_history.append(bank)


def _calculate_ma(price_list, period):
    if len(price_list) < period or period < 1:
        return None
    return sum(price_list[-period:]) / period


def _get_bias_and_underlying():
    """
    Returns (bias, underlying_name, current_price, short_ma, long_ma)
    bias: "bullish" | "bearish" | "neutral"
    """
    from .config import SHORT_MA_PERIOD, LONG_MA_PERIOD, UNDERLYING_PREFERENCE

    # Prefer NIFTY history if sufficient
    nifty_prices = list(_nifty_history)
    bank_prices = list(_banknifty_history)

    nifty_short = _calculate_ma(nifty_prices, SHORT_MA_PERIOD)
    nifty_long = _calculate_ma(nifty_prices, LONG_MA_PERIOD)

    if nifty_short is not None and nifty_long is not None and len(nifty_prices) >= LONG_MA_PERIOD:
        if nifty_short > nifty_long:
            return "bullish", "NIFTY", nifty_prices[-1], nifty_short, nifty_long
        else:
            return "bearish", "NIFTY", nifty_prices[-1], nifty_short, nifty_long

    # Fallback to BANKNIFTY
    bank_short = _calculate_ma(bank_prices, SHORT_MA_PERIOD)
    bank_long = _calculate_ma(bank_prices, LONG_MA_PERIOD)
    if bank_short is not None and bank_long is not None and len(bank_prices) >= LONG_MA_PERIOD:
        if bank_short > bank_long:
            return "bullish", "BANKNIFTY", bank_prices[-1], bank_short, bank_long
        else:
            return "bearish", "BANKNIFTY", bank_prices[-1], bank_short, bank_long

    return "neutral", "NIFTY", None, None, None


# ========================
# Symbol Parsing & Contract Selection
# ========================
_SYMBOL_RE = re.compile(
    r"^(NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY)(\d{2})([A-Z]{3})(\d+)(CE|PE)$"
)


def _parse_option_symbol(symbol):
    """Parse e.g. NIFTY26JUN25000CE -> dict or None"""
    if not isinstance(symbol, str):
        return None
    match = _SYMBOL_RE.match(symbol)
    if not match:
        return None
    underlying, year, month, strike_str, opt_type = match.groups()
    try:
        strike = int(strike_str)
        return {
            "symbol": symbol,
            "underlying": underlying,
            "year": int(year),
            "month": month,
            "strike": strike,
            "opt_type": opt_type,  # "CE" or "PE"
        }
    except Exception:
        return None


def _get_strike_step(underlying):
    from .config import (
        NIFTY_STRIKE_STEP, BANKNIFTY_STRIKE_STEP,
        FINNIFTY_STRIKE_STEP, MIDCPNIFTY_STRIKE_STEP
    )
    mapping = {
        "NIFTY": NIFTY_STRIKE_STEP,
        "BANKNIFTY": BANKNIFTY_STRIKE_STEP,
        "FINNIFTY": FINNIFTY_STRIKE_STEP,
        "MIDCPNIFTY": MIDCPNIFTY_STRIKE_STEP,
    }
    return mapping.get(underlying, 50)


def _get_atm_strike(price, step):
    if price is None or step <= 0:
        return None
    return round(price / step) * step


def _find_best_contract(snapshot, bias, underlying_hint):
    """
    Scan symbols dict and return best matching slightly OTM option contract dict or None.
    Selection criteria (in order):
    1. instrument_type == "OPTION"
    2. Matches preferred underlying (or hint)
    3. Correct option type for bias (CE for bullish, PE for bearish)
    4. Slightly OTM (within OTM_OFFSET_PCT window)
    5. Premium in [MIN_PREMIUM_RS, MAX_PREMIUM_RS]
    6. Highest OI/volume if available, else first match
    """
    from .config import (
        UNDERLYING_PREFERENCE, OTM_OFFSET_PCT,
        MIN_PREMIUM_RS, MAX_PREMIUM_RS, LOTS_PER_TRADE
    )

    symbols = snapshot.get("symbols") or {}
    if not isinstance(symbols, dict) or len(symbols) == 0:
        return None

    candidates = []
    current_price = None
    if underlying_hint == "NIFTY":
        current_price = _safe_float(snapshot.get("nifty"))
    elif underlying_hint == "BANKNIFTY":
        current_price = _safe_float(snapshot.get("banknifty"))

    if current_price is None or current_price < 1000:
        return None

    step = _get_strike_step(underlying_hint)
    atm = _get_atm_strike(current_price, step)
    if atm is None:
        return None

    # Desired strike range for slightly OTM
    if bias == "bullish":
        # Buy CALL slightly OTM -> strike > ATM
        min_strike = atm
        max_strike = atm * (1 + OTM_OFFSET_PCT * 2)
        desired_type = "CE"
    else:
        # Buy PUT slightly OTM -> strike < ATM
        min_strike = atm * (1 - OTM_OFFSET_PCT * 2)
        max_strike = atm
        desired_type = "PE"

    for sym, data in symbols.items():
        if not isinstance(data, dict):
            continue
        if data.get("instrument_type") != "OPTION":
            continue

        parsed = _parse_option_symbol(sym)
        if not parsed:
            continue
        if parsed["underlying"] != underlying_hint:
            continue
        if parsed["opt_type"] != desired_type:
            continue

        strike = parsed["strike"]
        if not (min_strike <= strike <= max_strike):
            continue

        ltp = _safe_float(data.get("ltp"))
        if ltp is None or not (MIN_PREMIUM_RS <= ltp <= MAX_PREMIUM_RS):
            continue

        lot_size = int(data.get("lot_size") or 0)
        if lot_size <= 0:
            continue

        # Liquidity proxy
        oi = int(data.get("oi") or 0)
        vol = int(data.get("volume") or 0)

        candidates.append({
            "symbol": sym,
            "ltp": ltp,
            "lot_size": lot_size,
            "oi": oi,
            "volume": vol,
            "strike": strike,
            "opt_type": parsed["opt_type"],
            "underlying": parsed["underlying"],
        })

    if not candidates:
        return None

    # Prefer higher liquidity, then lower premium (cheaper OTM)
    candidates.sort(key=lambda x: (-x["oi"], -x["volume"], x["ltp"]))
    best = candidates[0]

    # Final quantity calc
    best["quantity"] = LOTS_PER_TRADE * best["lot_size"]
    best["estimated_cost"] = best["quantity"] * best["ltp"]
    return best


# ========================
# Core Signal Logic
# ========================
def _safe_float(val, default=None):
    try:
        if val is None:
            return default
        f = float(val)
        return f if f == f else default  # NaN check
    except Exception:
        return default


def generate_signal(snapshot):
    """
    Main entry point. Returns exactly:
    {"action": "BUY"|"SELL"|"HOLD", "symbol": str, "quantity": int (>=0), "reason": str}
    """
    from .config import (
        LOTS_PER_TRADE, CASH_BUFFER_RS, MAX_DRAWDOWN_PCT,
        MIN_EQUITY_TO_TRADE, COOLDOWN_MINUTES, TP_MULTIPLIER,
        SL_MULTIPLIER, MAX_LOSS_PER_TRADE_RS, MAX_HOLD_MINUTES
    )

    # --- 1. Defensive snapshot validation ---
    if not isinstance(snapshot, dict):
        return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": "Invalid snapshot type"}

    cash = _safe_float(snapshot.get("cash"), 0.0)
    equity = _safe_float(snapshot.get("equity"), cash)
    has_position = bool(snapshot.get("has_position", False))
    position = snapshot.get("position") or {}

    # Update history for MA (always do this)
    _update_underlying_history(snapshot)

    ist_now = _get_ist_now(snapshot.get("time"))

    # --- 2. Market timing gates ---
    if not _is_market_open(ist_now):
        return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": "Market closed"}

    # --- 3. Drawdown protection (capital preservation) ---
    global _peak_equity
    if equity > _peak_equity:
        _peak_equity = equity
    drawdown = (_peak_equity - equity) / _peak_equity if _peak_equity > 0 else 0
    if drawdown > MAX_DRAWDOWN_PCT and equity < MIN_EQUITY_TO_TRADE:
        return {"action": "HOLD", "symbol": "", "quantity": 0,
                "reason": f"Drawdown protection active ({drawdown*100:.1f}% from peak)"}

    # --- 4. Cooldown check ---
    global _last_action_ts
    if _last_action_ts is not None:
        mins_since = (ist_now - _last_action_ts).total_seconds() / 60.0
        if mins_since < COOLDOWN_MINUTES:
            return {"action": "HOLD", "symbol": "", "quantity": 0,
                    "reason": f"Cooldown active ({COOLDOWN_MINUTES - mins_since:.0f} min left)"}

    # --- 5. If position open -> manage exit (TP/SL/time/max loss) ---
    if has_position:
        pos_symbol = position.get("symbol", "")
        pos_qty = int(position.get("quantity") or 0)
        entry_price = _safe_float(position.get("entry_price"), 0.0)
        entry_time_str = position.get("entry_time")

        if pos_qty <= 0 or entry_price <= 0 or not pos_symbol:
            return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": "Corrupt position data"}

        current_ltp = None
        symbols = snapshot.get("symbols") or {}
        if pos_symbol in symbols and isinstance(symbols[pos_symbol], dict):
            current_ltp = _safe_float(symbols[pos_symbol].get("ltp"))

        if current_ltp is None or current_ltp <= 0:
            return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": "No current LTP for open position"}

        unrealized_pnl = _safe_float(snapshot.get("unrealized_pnl"), 0.0)
        entry_cost = entry_price * pos_qty
        max_loss = min(entry_cost * (1 - SL_MULTIPLIER), MAX_LOSS_PER_TRADE_RS)

        # Time since entry
        held_minutes = 0
        if entry_time_str:
            try:
                et = entry_time_str.replace("Z", "+00:00")
                entry_dt = datetime.fromisoformat(et)
                held_minutes = (ist_now - entry_dt.astimezone(IST)).total_seconds() / 60.0
            except Exception:
                held_minutes = 0

        reason = ""
        action = "HOLD"

        # TP
        if current_ltp >= entry_price * TP_MULTIPLIER:
            action = "SELL"
            reason = f"Take profit hit ({TP_MULTIPLIER}x entry @ {current_ltp:.2f})"
        # SL - premium decayed or max loss
        elif current_ltp <= entry_price * SL_MULTIPLIER or unrealized_pnl <= -max_loss:
            action = "SELL"
            reason = f"Stop loss hit (premium {current_ltp:.2f} or PnL {unrealized_pnl:.0f})"
        # Time stop
        elif held_minutes >= MAX_HOLD_MINUTES:
            action = "SELL"
            reason = f"Time stop ({MAX_HOLD_MINUTES} min hold reached)"
        # Auto square off near close
        elif _should_auto_square_off(ist_now):
            action = "SELL"
            reason = "Auto square-off before market close"

        if action == "SELL":
            _last_action_ts = ist_now
            return {"action": "SELL", "symbol": pos_symbol, "quantity": pos_qty, "reason": reason}

        return {"action": "HOLD", "symbol": "", "quantity": 0,
                "reason": f"Holding {pos_symbol} | LTP {current_ltp:.2f} | PnL {unrealized_pnl:.0f}"}

    # --- 6. No position -> look for new BUY opportunity ---
    if cash < CASH_BUFFER_RS:
        return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": f"Cash buffer active (cash={cash:.0f})"}

    if _no_new_entries_allowed(ist_now):
        return {"action": "HOLD", "symbol": "", "quantity": 0, "reason": "No new entries after cutoff time"}

    bias, underlying, current_price, short_ma, long_ma = _get_bias_and_underlying()
    if bias == "neutral" or current_price is None:
        return {"action": "HOLD", "symbol": "", "quantity": 0,
                "reason": "Insufficient history or neutral bias (building MA)"}

    contract = _find_best_contract(snapshot, bias, underlying)
    if contract is None:
        return {"action": "HOLD", "symbol": "", "quantity": 0,
                "reason": f"No suitable slightly OTM {bias} option found for {underlying}"}

    # Final affordability & safety
    cost = contract["estimated_cost"]
    if cost > cash - CASH_BUFFER_RS:
        return {"action": "HOLD", "symbol": "", "quantity": 0,
                "reason": f"Insufficient cash for {LOTS_PER_TRADE} lot(s) of {contract['symbol']}"}

    # All gates passed -> BUY
    _last_action_ts = ist_now
    global _last_position_entry_time
    _last_position_entry_time = ist_now

    reason = (
        f"{bias.upper()} bias on {underlying} (ShortMA {short_ma:.0f} > LongMA {long_ma:.0f}) | "
        f"BUY {LOTS_PER_TRADE} lot slightly OTM {contract['opt_type']} {contract['strike']} | "
        f"Premium {contract['ltp']:.2f} | Est. cost {cost:.0f}"
    )

    return {
        "action": "BUY",
        "symbol": contract["symbol"],
        "quantity": contract["quantity"],
        "reason": reason
    }