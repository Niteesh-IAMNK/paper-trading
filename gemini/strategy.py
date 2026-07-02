"""
Core algorithmic engine for Alpha-Confluence Trend System.
Focuses strictly on evaluating market structure, computing indicators, 
and maximizing geometric portfolio compounding through dynamic lot sizing.
"""

from shared.config import INITIAL_CAPITAL

from . import config

# In-memory state tracking for indicators and peak profit tracking
_market_history = []
_trade_peaks = {}  # Tracks highest premium seen for active symbols: {symbol: highest_price}


def generate_signal(snapshot: dict) -> dict:
    """
    Main evaluation loop. Processes market data and returns execution actions.
    The engine handles all timing, cash validation, and execution logic.
    """
    global _market_history, _trade_peaks

    # 1. Parsing Context
    if not isinstance(snapshot, dict):
        return _hold("Invalid snapshot structure.")

    nifty_price = snapshot.get("nifty")
    equity = snapshot.get("equity", float(INITIAL_CAPITAL))
    has_position = snapshot.get("has_position", False)
    open_position = snapshot.get("position")
    
    ce_symbol = snapshot.get("ce_symbol")
    pe_symbol = snapshot.get("pe_symbol")
    ce_price = snapshot.get("ce_price")
    pe_price = snapshot.get("pe_price")
    symbols_data = snapshot.get("symbols", {})

    if not isinstance(nifty_price, (int, float)) or nifty_price <= 0:
        return _hold("Awaiting valid Nifty pricing.")

    # 2. Update Historical Data for Indicators
    nifty_data = symbols_data.get("NIFTY", {})
    volume = nifty_data.get("volume", 1)
    
    prev_vwap_num = _market_history[-1]["vwap_num"] if _market_history else 0.0
    prev_vwap_den = _market_history[-1]["vwap_den"] if _market_history else 0.0
    
    current_vwap_num = prev_vwap_num + (nifty_price * volume)
    current_vwap_den = prev_vwap_den + volume

    _market_history.append({
        "price": nifty_price,
        "volume": volume,
        "vwap_num": current_vwap_num,
        "vwap_den": current_vwap_den
    })

    if len(_market_history) > config.HISTORY_LIMIT:
        _market_history.pop(0)

    # 3. Manage Active Position (Dynamic Trailing Stop)
    if has_position and open_position:
        return _manage_active_position(open_position, symbols_data, ce_symbol, ce_price, pe_symbol, pe_price)

    # 4. Indicator Warm-up Check
    if len(_market_history) < config.MACD_SLOW + config.MACD_SIGNAL + 2:
        return _hold("Warming up indicator buffers.")

    # 5. Compute Technical Indicators
    prices = [tick["price"] for tick in _market_history]
    
    current_vwap = current_vwap_num / current_vwap_den if current_vwap_den > 0 else nifty_price
    
    ema_fast = _calc_ema(prices, config.EMA_FAST)
    ema_slow = _calc_ema(prices, config.EMA_SLOW)
    rsi = _calc_rsi(prices, config.RSI_PERIOD)
    _, _, macd_hist = _calc_macd(prices, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
    
    # Analyze velocity by comparing against the previous tick
    prev_prices = prices[:-1]
    prev_ema_fast = _calc_ema(prev_prices, config.EMA_FAST)
    prev_ema_slow = _calc_ema(prev_prices, config.EMA_SLOW)
    _, _, prev_macd_hist = _calc_macd(prev_prices, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)

    # 6. Evaluate Trade Setups
    bullish_cross = ema_fast[-1] > ema_slow[-1] and prev_ema_fast[-1] <= prev_ema_slow[-1]
    bearish_cross = ema_fast[-1] < ema_slow[-1] and prev_ema_fast[-1] >= prev_ema_slow[-1]

    target_symbol = None
    target_price = None
    reason = ""
    confidence_multiplier = 1.0

    # Long Setup (CE)
    if bullish_cross and nifty_price > current_vwap and rsi > 55 and macd_hist > 0:
        if ce_symbol and ce_price and ce_price > 0:
            target_symbol = ce_symbol
            target_price = ce_price
            reason = "Bullish Momentum Breakout."
            
            # Upscale position size if momentum velocity is extreme
            if rsi > 65: confidence_multiplier += 0.5
            if macd_hist > (prev_macd_hist * 1.5): confidence_multiplier += 0.5

    # Short Setup (PE)
    elif bearish_cross and nifty_price < current_vwap and rsi < 45 and macd_hist < 0:
        if pe_symbol and pe_price and pe_price > 0:
            target_symbol = pe_symbol
            target_price = pe_price
            reason = "Bearish Momentum Breakdown."
            
            # Upscale position size if momentum velocity is extreme
            if rsi < 35: confidence_multiplier += 0.5
            if macd_hist < (prev_macd_hist * 1.5): confidence_multiplier += 0.5

    # 7. Dynamic Position Sizing & Execution
    if target_symbol and target_price:
        # Base lots calculated geometrically via equity tiers (e.g., 5L equity = 10 Base Lots)
        base_lots = int(max(1, equity // config.EQUITY_PER_LOT_TIER))
        
        # Scale lots based on trade setup confidence
        target_lots = int(base_lots * confidence_multiplier)
        target_lots = max(1, target_lots)

        # Reset peak tracker for the new trade
        _trade_peaks[target_symbol] = target_price

        return {
            "action": "BUY",
            "symbol": target_symbol,
            "lots": target_lots,
            "reason": f"{reason} (Base Lots: {base_lots}, Multiplier: {confidence_multiplier}x)",
            "confidence": round(confidence_multiplier, 2)
        }

    return _hold("Monitoring. No systemic momentum trigger.")


def _manage_active_position(position: dict, symbols_data: dict, ce_sym: str, ce_px: float, pe_sym: str, pe_px: float) -> dict:
    """
    Manages active trades using a high-water mark trailing stop to ride compounding trends,
    while utilizing strict structural breakdown exits.
    """
    global _trade_peaks
    
    symbol = position.get("symbol")
    entry_price = position.get("entry_price")

    if not symbol or not entry_price or entry_price <= 0:
        return _hold("Position state unreadable.")

    current_ltp = None
    if symbol == ce_sym:
        current_ltp = ce_px
    elif symbol == pe_sym:
        current_ltp = pe_px
    elif symbol in symbols_data:
        current_ltp = symbols_data[symbol].get("ltp")

    if not current_ltp or current_ltp <= 0:
        return _hold("Awaiting valid pricing for active position.")

    # Track maximum premium reached to inform the trailing stop
    max_seen = _trade_peaks.get(symbol, entry_price)
    if current_ltp > max_seen:
        _trade_peaks[symbol] = current_ltp
        max_seen = current_ltp

    performance_pct = (current_ltp - entry_price) / entry_price

    # 1. Hard Stop Loss (Preservation of compounding base)
    if performance_pct <= -config.STOP_LOSS_PCT:
        return _generate_exit(symbol, f"Hard stop hit ({performance_pct * 100:.2f}%).")

    # 2. Dynamic Trailing Stop (Securing the ride)
    if max_seen >= entry_price * (1 + config.TRAIL_ACTIVATION_PCT):
        # Tighten the stop if we hit massive upside to lock in the windfall
        current_pullback = config.TRAIL_TIGHTEN_PCT if (max_seen >= entry_price * 1.60) else config.TRAIL_PULLBACK_PCT
        trail_stop_price = max_seen * (1 - current_pullback)
        
        if current_ltp <= trail_stop_price:
            return _generate_exit(symbol, f"Peak Trailing Stop triggered. Peak: {max_seen:.2f}, Exit: {current_ltp:.2f}")

    # 3. Structural Breakdown Exit
    if len(_market_history) >= config.EMA_FAST + 1:
        prices = [tick["price"] for tick in _market_history]
        ema_fast = _calc_ema(prices, config.EMA_FAST)[-1]
        current_underlying = prices[-1]
        
        if "CE" in symbol and current_underlying < ema_fast and performance_pct > 0:
            return _generate_exit(symbol, "Structure Breakdown: Index closed below 9 EMA.")
            
        if "PE" in symbol and current_underlying > ema_fast and performance_pct > 0:
            return _generate_exit(symbol, "Structure Breakdown: Index closed above 9 EMA.")

    return _hold(f"Tracking {symbol}. PnL: {performance_pct * 100:.2f}%. Peak: {max_seen:.2f}")


# ==========================================
# Technical Indicator Helpers
# ==========================================

def _calc_ema(data: list, period: int) -> list:
    if len(data) < period:
        return data
    ema = [sum(data[:period]) / period]
    multiplier = 2 / (period + 1)
    for price in data[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

def _calc_rsi(data: list, period: int) -> float:
    if len(data) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    for i in range(1, len(data)):
        change = data[i] - data[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
        
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(data) - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def _calc_macd(data: list, fast: int, slow: int, signal: int) -> tuple:
    ema_fast = _calc_ema(data, fast)
    ema_slow = _calc_ema(data, slow)
    
    min_len = min(len(ema_fast), len(ema_slow))
    if min_len == 0:
        return 0, 0, 0

    macd_line = [ema_fast[-min_len + i] - ema_slow[-min_len + i] for i in range(min_len)]
    signal_line = _calc_ema(macd_line, signal)
    
    if not signal_line or not macd_line:
        return 0, 0, 0
        
    macd_hist = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], macd_hist


# ==========================================
# Structural Helpers
# ==========================================

def _generate_exit(symbol: str, reason: str) -> dict:
    return {
        "action": "SELL",
        "symbol": symbol,
        "reason": reason
    }

def _hold(reason: str) -> dict:
    return {
        "action": "HOLD",
        "symbol": "",
        "reason": reason
    }