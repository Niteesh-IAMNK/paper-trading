"""
Core algorithmic execution engine for NSE Index Derivatives (Options/Futures).
Implements state tracking, lot-size management, and defensive risk guardrails.
"""

from datetime import datetime, time
import math
from .config import (
    STRATEGY_NAME,
    BASE_UNDERLYING,
    SYMBOL_FILTER_KEYWORD,
    SHORT_WINDOW,
    LONG_WINDOW,
    MAX_LOTS_PER_TRADE,
    CAPITAL_RESERVE_PCT,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    MAX_DAILY_DRAWDOWN_PCT,
    AUTO_SQUARE_OFF_TIME,
    COOLDOWN_PERIOD_SECONDS
)

# Persistent state containers (In-Memory persistency during execution runtime)
_underlying_history = []
_last_trade_timestamp = None
_initial_day_equity = None


def generate_signal(snapshot: dict) -> dict:
    """
    Exposed entry point called by the execution loop.
    Processes market data snapshot and returns verified execution instructions.
    """
    global _underlying_history, _last_trade_timestamp, _initial_day_equity

    # 1. Graceful extraction and parsing of structural fields
    if not isinstance(snapshot, dict):
        return _hold_signal("Invaid snapshot format received.")

    current_time_str = snapshot.get("time")
    underlying_price = snapshot.get(BASE_UNDERLYING)
    cash = snapshot.get("cash", 0.0)
    equity = snapshot.get("equity", 0.0)
    has_position = snapshot.get("has_position", False)
    open_position = snapshot.get("position")
    symbols_data = snapshot.get("symbols", {})

    if underlying_price is None or not isinstance(underlying_price, (int, float)) or underlying_price <= 0:
        return _hold_signal("Invalid or missing underlying index price data.")

    # 2. Parse Timestamp safely
    parsed_dt = _safe_parse_time(current_time_str)
    
    # 3. Handle Daily Drawdown Protection state
    if _initial_day_equity is None and equity > 0:
        _initial_day_equity = equity

    if _initial_day_equity and equity > 0:
        current_drawdown = (_initial_day_equity - equity) / _initial_day_equity
        if current_drawdown >= MAX_DAILY_DRAWDOWN_PCT:
            if has_position and open_position:
                return _generate_exit(open_position, symbols_data, "Max daily drawdown ceiling breached. Risk halt.")
            return _hold_signal("Trading halted due to daily drawdown threshold breach.")

    # 4. Handle Time-Based Auto Square-Off Check
    if parsed_dt:
        sq_off_hour, sq_off_min, sq_off_sec = map(int, AUTO_SQUARE_OFF_TIME.split(":"))
        if parsed_dt.time() >= time(sq_off_hour, sq_off_min, sq_off_sec):
            if has_position and open_position:
                return _generate_exit(open_position, symbols_data, "Auto square-off time limit reached.")
            return _hold_signal("Market window closing. Safe state.")

    # 5. Manage Risk Boundaries on Active Position
    if has_position and open_position:
        return _manage_risk_metrics(open_position, symbols_data)

    # 6. Update historical analytical trends
    _underlying_history.append(underlying_price)
    if len(_underlying_history) > (LONG_WINDOW * 2):
        _underlying_history.pop(0)

    # Validate signal buffer warm up status
    if len(_underlying_history) < LONG_WINDOW:
        return _hold_signal(f"Building index trend history. {len(_underlying_history)}/{LONG_WINDOW}")

    # 7. Check Cooldown metrics prior to processing entry logic
    if _last_trade_timestamp and parsed_dt:
        elapsed_time = (parsed_dt - _last_trade_timestamp).total_seconds()
        if elapsed_time < COOLDOWN_PERIOD_SECONDS:
            return _hold_signal(f"Execution cooldown phase active. Seconds remaining: {COOLDOWN_PERIOD_SECONDS - elapsed_time:.1f}")

    # 8. Compute Signal Metrics (Moving Average Crossover on Underlying Index)
    short_ma = sum(_underlying_history[-SHORT_WINDOW:]) / SHORT_WINDOW
    long_ma = sum(_underlying_history[-LONG_WINDOW:]) / LONG_WINDOW
    prev_short_ma = sum(_underlying_history[-SHORT_WINDOW - 1:-1]) / SHORT_WINDOW
    prev_long_ma = sum(_underlying_history[-LONG_WINDOW - 1:-1]) / LONG_WINDOW

    bullish_trend = short_ma > long_ma and prev_short_ma <= prev_long_ma

    # 9. Evaluate Entry Setup
    if bullish_trend:
        target_instrument, target_data = _find_tradeable_instrument(symbols_data, underlying_price)
        if not target_instrument or not target_data:
            return _hold_signal("No valid matching tradeable derivative instruments available.")

        ltp = target_data.get("ltp")
        lot_size = target_data.get("lot_size")

        if not ltp or not lot_size or ltp <= 0 or lot_size <= 0:
            return _hold_signal("Target instrument displays corrupt pricing or lot configurations.")

        # Compute deterministic position sizing constraints
        usable_cash = cash * (1.0 - CAPITAL_RESERVE_PCT)
        max_affordable_qty = usable_cash // ltp
        max_affordable_lots = max_affordable_qty // lot_size

        target_lots = min(max_affordable_lots, MAX_LOTS_PER_TRADE)
        final_quantity = int(target_lots * lot_size)

        if final_quantity <= 0:
            return _hold_signal(f"Insufficient trade capital to acquire 1 full contract lot size ({lot_size}).")

        # Double check safety logic
        if (final_quantity * ltp) > cash:
            return _hold_signal("Defensive override: calculated cost exceeds real available cash.")

        _last_trade_timestamp = parsed_dt
        return {
            "action": "BUY",
            "symbol": target_instrument,
            "quantity": final_quantity,
            "reason": f"Bullish index cross detected. Target instrument premium: {ltp}"
        }

    return _hold_signal("No dynamic derivative trigger matched.")


def _manage_risk_metrics(position: dict, symbols_data: dict) -> dict:
    """
    Monitors underlying market values to enforce stop-loss and take-profit mechanisms.
    """
    symbol = position.get("symbol")
    entry_price = position.get("entry_price")
    quantity = position.get("quantity", 0)

    if not symbol or not entry_price or entry_price <= 0 or quantity <= 0:
        return _hold_signal("Open tracking state exhibits corruption. Analyzing next frame.")

    instrument_data = symbols_data.get(symbol)
    if not instrument_data:
        return _hold_signal(f"Active trade symbol {symbol} unavailable in recent market snapshot mapping.")

    current_ltp = instrument_data.get("ltp")
    if not current_ltp or current_ltp <= 0:
        return _hold_signal(f"Skipping tracking cycle; tracking instrument {symbol} returned invalid execution price.")

    # Calculate absolute premium variance performance
    performance_pct = (current_ltp - entry_price) / entry_price

    if performance_pct <= -STOP_LOSS_PCT:
        return _generate_exit(position, symbols_data, f"Stop loss breached at {performance_pct * 100:.2f}%")

    if performance_pct >= TAKE_PROFIT_PCT:
        return _generate_exit(position, symbols_data, f"Take profit achieved at {performance_pct * 100:.2f}%")

    return _hold_signal(f"Tracking trade {symbol}. Unconfirmed variance performance: {performance_pct * 100:.2f}%")


def _find_tradeable_instrument(symbols_data: dict, index_price: float) -> tuple:
    """
    Locates the most relevant tradeable target instrument inside the available snapshot mapping.
    Prioritizes Calls (CE) near the money when riding a bullish indicator trend.
    """
    best_symbol = None
    best_data = None
    min_strike_diff = float('inf')

    for sym, metadata in symbols_data.items():
        if SYMBOL_FILTER_KEYWORD not in sym:
            continue

        # Simple verification of correct schema mapping parsing
        if not isinstance(metadata, dict) or "ltp" not in metadata or "lot_size" not in metadata:
            continue

        # Look for instruments that have a valid call signature option context or generic future
        if "CE" in sym or "FUT" in sym:
            # Parse approximate proximity to handle strike offsets neatly if present in string
            # Extracted numerical matches serve to optimize proximity search maps
            digits = ''.join(c for c in sym if c.isdigit())
            if digits:
                try:
                    # Capture the last 5 characters numeric segment representing strike level
                    strike_val = float(digits[-5:])
                    diff = abs(strike_val - index_price)
                    if diff < min_strike_diff:
                        min_strike_diff = diff
                        best_symbol = sym
                        best_data = metadata
                except ValueError:
                    # Default selection fallback logic if token string extraction hits complex anomalies
                    if best_symbol is None:
                        best_symbol = sym
                        best_data = metadata
            else:
                if best_symbol is None:
                    best_symbol = sym
                    best_data = metadata

    return best_symbol, best_data


def _generate_exit(position: dict, symbols_data: dict, system_reason: str) -> dict:
    """
    Builds structured, normalized exit directions confirming parameter safety targets.
    """
    symbol = position.get("symbol", "")
    quantity = position.get("quantity", 0)

    # Ensure quantity returned is an absolute scalar integer
    if isinstance(quantity, float):
        quantity = int(math.floor(quantity))

    return {
        "action": "SELL",
        "symbol": symbol,
        "quantity": max(0, quantity),
        "reason": system_reason
    }


def _hold_signal(narrative_reason: str) -> dict:
    """
    Builds a uniform strategy HOLD packet structure.
    """
    return {
        "action": "HOLD",
        "symbol": "",
        "quantity": 0,
        "reason": narrative_reason
    }


def _safe_parse_time(time_str: str):
    """
    Safely string-parses incoming ISO date format signatures.
    Defends cleanly against unexpected structural gaps.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        # Handles typical standard ISO execution string signatures cleanly
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            # Secondary fallback parsing layout boundary check
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return None