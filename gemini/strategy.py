"""
Core algorithmic execution engine for Alpha-Confluence Trend System.
Implements EMA, VWAP, RSI, MACD logic using standard Python libraries.
Ensures strict defensive programming and capital preservation.
"""

from datetime import datetime, time
import math
from . import config

# In-memory state tracking for indicators and risk limits
_market_history = []  # Stores dicts: {"price": float, "volume": int, "vwap_num": float, "vwap_den": float}
_initial_day_equity = None
_trades_today = 0
_last_trade_date = None


def generate_signal(snapshot: dict) -> dict:
    """
    Main evaluation loop. Processes market data, builds indicators, and returns execution actions.
    """
    global _market_history, _initial_day_equity, _trades_today, _last_trade_date

    # 1. Structural Validation & Parsing
    if not isinstance(snapshot, dict):
        return _hold("Invalid snapshot structure.")

    current_time_str = snapshot.get("time")
    nifty_price = snapshot.get("nifty")
    cash = snapshot.get("cash", 0.0)
    equity = snapshot.get("equity", 0.0)
    has_position = snapshot.get("has_position", False)
    open_position = snapshot.get("position")
    
    ce_symbol = snapshot.get("ce_symbol")
    pe_symbol = snapshot.get("pe_symbol")
    ce_price = snapshot.get("ce_price")
    pe_price = snapshot.get("pe_price")
    symbols_data = snapshot.get("symbols", {})

    if not isinstance(nifty_price, (int, float)) or nifty_price <= 0:
        return _hold("Invalid or missing underlying Nifty price.")

    parsed_dt = _safe_parse_time(current_time_str)
    if not parsed_dt:
        return _hold("Invalid or missing timestamp.")
    
    current_time = parsed_dt.time()
    current_date = parsed_dt.date()

    # 2. Reset Daily State & Track Drawdown
    if _last_trade_date != current_date:
        _market_history = []
        _initial_day_equity = equity if equity > 0 else cash
        _trades_today = 0
        _last_trade_date = current_date

    if _initial_day_equity and equity > 0:
        current_drawdown = (_initial_day_equity - equity) / _initial_day_equity
        if current_drawdown >= config.MAX_DAILY_DRAWDOWN_PCT:
            if has_position and open_position:
                return _generate_exit(open_position, "Max daily drawdown ceiling breached (5%).")
            return _hold("Trading halted due to daily drawdown threshold.")

    # 3. Time Constraints Verification
    try:
        start_time = time(*map(int, config.TRADE_START_TIME.split(":")))
        sq_off_time = time(*map(int, config.AUTO_SQUARE_OFF_TIME.split(":")))
    except ValueError:
        return _hold("System time configuration error.")

    if current_time >= sq_off_time:
        if has_position and open_position:
            return _generate_exit(open_position, "Auto square-off time reached.")
        return _hold("Market closing window. No new positions.")

    # 4. Update Historical Data (Prices and Volume for Index)
    # FYERS snapshot might not have index volume directly, we use a proxy 1 if missing,
    # but preferably extract it from the symbols mapping if available.
    nifty_data = symbols_data.get("NIFTY", {})
    volume = nifty_data.get("volume", 1)  # Fallback to 1 to allow time-weighted VWAP if vol missing
    
    # Calculate cumulative VWAP components for the day
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

    # 5. Manage Active Position (Dynamic Stops & Take Profits)
    if has_position and open_position:
        return _manage_active_position(open_position, symbols_data, ce_symbol, ce_price, pe_symbol, pe_price)

    # 6. Trade Frequency & Warm-up Checks
    if current_time < start_time:
        return _hold("Market stabilizing. Awaiting trade start window.")
        
    if _trades_today >= config.MAX_DAILY_TRADES:
        return _hold(f"Daily trade limit ({config.MAX_DAILY_TRADES}) reached.")

    if len(_market_history) < config.MACD_SLOW + config.MACD_SIGNAL + 1:
        return _hold(f"Warming up indicator buffers ({len(_market_history)}/{config.MACD_SLOW + config.MACD_SIGNAL}).")

    # 7. Compute Technical Indicators
    prices = [tick["price"] for tick in _market_history]
    volumes = [tick["volume"] for tick in _market_history]
    
    current_vwap = current_vwap_num / current_vwap_den if current_vwap_den > 0 else nifty_price
    
    ema_fast = _calc_ema(prices, config.EMA_FAST)
    ema_slow = _calc_ema(prices, config.EMA_SLOW)
    rsi = _calc_rsi(prices, config.RSI_PERIOD)
    macd_line, macd_signal, macd_hist = _calc_macd(prices, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
    
    # Volume confirmation
    vol_sma = sum(volumes[-config.VOLUME_SMA_PERIOD:]) / config.VOLUME_SMA_PERIOD
    vol_confirmed = volumes[-1] > vol_sma

    # Check crossovers securely by looking at previous period EMA
    prev_prices = prices[:-1]
    prev_ema_fast = _calc_ema(prev_prices, config.EMA_FAST)
    prev_ema_slow = _calc_ema(prev_prices, config.EMA_SLOW)

    # 8. Evaluate Trade Setups
    bullish_cross = ema_fast[-1] > ema_slow[-1] and prev_ema_fast[-1] <= prev_ema_slow[-1]
    bearish_cross = ema_fast[-1] < ema_slow[-1] and prev_ema_fast[-1] >= prev_ema_slow[-1]

    target_symbol = None
    target_price = None
    reason = ""

    # Long Setup (CE)
    if bullish_cross and nifty_price > current_vwap and rsi > 60 and macd_hist > 0 and vol_confirmed:
        if ce_symbol and ce_price and ce_price > 0:
            target_symbol = ce_symbol
            target_price = ce_price
            reason = "Bullish Confluence Setup: VWAP+EMA+RSI+MACD+VOL."

    # Short Setup (PE)
    elif bearish_cross and nifty_price < current_vwap and rsi < 40 and macd_hist < 0 and vol_confirmed:
        if pe_symbol and pe_price and pe_price > 0:
            target_symbol = pe_symbol
            target_price = pe_price
            reason = "Bearish Confluence Setup: VWAP+EMA+RSI+MACD+VOL."

    # 9. Execute Position Sizing & Entry
    if target_symbol and target_price:
        lot_size = config.DEFAULT_LOT_SIZE
        if target_symbol in symbols_data:
            lot_size = symbols_data[target_symbol].get("lot_size", config.DEFAULT_LOT_SIZE)
            
        allocated_capital = cash * config.CAPITAL_ALLOCATION_PCT
        affordable_qty = allocated_capital // target_price
        affordable_lots = int(affordable_qty // lot_size)
        
        target_lots = min(max(1, affordable_lots), config.MAX_LOTS_PER_TRADE)
        final_quantity = int(target_lots * lot_size)

        if final_quantity <= 0:
            return _hold("Insufficient capital for 1 lot based on allocation limits.")

        if (final_quantity * target_price) > cash:
            return _hold("Defensive override: Trade cost exceeds available cash.")

        _trades_today += 1
        return {
            "action": "BUY",
            "symbol": target_symbol,
            "quantity": final_quantity,
            "reason": reason
        }

    return _hold("Monitoring. No systemic confluence trigger.")


def _manage_active_position(position: dict, symbols_data: dict, ce_sym: str, ce_px: float, pe_sym: str, pe_px: float) -> dict:
    """
    Manages dynamic trailing stop loss and system exits for an active trade.
    """
    symbol = position.get("symbol")
    entry_price = position.get("entry_price")

    if not symbol or not entry_price or entry_price <= 0:
        return _hold("Position state corrupted.")

    current_ltp = None
    if symbol == ce_sym:
        current_ltp = ce_px
    elif symbol == pe_sym:
        current_ltp = pe_px
    elif symbol in symbols_data:
        current_ltp = symbols_data[symbol].get("ltp")

    if not current_ltp or current_ltp <= 0:
        return _hold("Awaiting valid pricing for active position.")

    performance_pct = (current_ltp - entry_price) / entry_price

    # 1. Take Profit
    if performance_pct >= config.TAKE_PROFIT_PCT:
        return _generate_exit(position, f"Take profit hit ({performance_pct * 100:.2f}%).")

    # 2. Hard Stop Loss
    if performance_pct <= -config.STOP_LOSS_PCT:
        return _generate_exit(position, f"Hard stop loss hit ({performance_pct * 100:.2f}%).")

    # 3. Breakeven Trailing Logic
    # In a real environment, this would alter a database trait. We emulate it logically.
    # If the market drops back to breakeven AFTER hitting 10% profit.
    # Note: We can't strictly track the "high water mark" across snapshots purely statelessly 
    # without a custom DB field, but we can enforce a hard rule: if we are at -1% and it's 
    # not the first tick, we let it ride till the hard stop. For true trailing, 
    # we exit if performance dips below 0 if it ever touched 10%.
    # To keep it standard library and robust without complex state dicts:
    
    # Check underlying dynamic trail via EMA-9 crossover exit
    if len(_market_history) >= config.EMA_FAST + 1:
        prices = [tick["price"] for tick in _market_history]
        ema_fast = _calc_ema(prices, config.EMA_FAST)[-1]
        current_underlying = prices[-1]
        
        # CE Trailing Exit: Underlying closes below 9 EMA
        if "CE" in symbol and current_underlying < ema_fast and performance_pct > 0:
            return _generate_exit(position, "Trailing Stop: Index closed below 9 EMA.")
            
        # PE Trailing Exit: Underlying closes above 9 EMA
        if "PE" in symbol and current_underlying > ema_fast and performance_pct > 0:
            return _generate_exit(position, "Trailing Stop: Index closed above 9 EMA.")

    return _hold(f"Tracking trade {symbol}. PnL: {performance_pct * 100:.2f}%")


# ==========================================
# Technical Indicator Helpers
# ==========================================

def _calc_ema(data: list, period: int) -> list:
    """Calculates Exponential Moving Average recursively."""
    if len(data) < period:
        return data
    ema = [sum(data[:period]) / period]  # SMA for initial value
    multiplier = 2 / (period + 1)
    for price in data[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

def _calc_rsi(data: list, period: int) -> float:
    """Calculates Wilder's Relative Strength Index."""
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
    """Calculates MACD Line, Signal Line, and Histogram."""
    ema_fast = _calc_ema(data, fast)
    ema_slow = _calc_ema(data, slow)
    
    # Align lists to calculate MACD line
    min_len = min(len(ema_fast), len(ema_slow))
    macd_line = [ema_fast[-min_len + i] - ema_slow[-min_len + i] for i in range(min_len)]
    
    signal_line = _calc_ema(macd_line, signal)
    
    if not signal_line or not macd_line:
        return 0, 0, 0
        
    macd_hist = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], macd_hist

# ==========================================
# Structural Helpers
# ==========================================

def _generate_exit(position: dict, system_reason: str) -> dict:
    symbol = position.get("symbol", "")
    quantity = int(math.floor(position.get("quantity", 0)))
    return {
        "action": "SELL",
        "symbol": symbol,
        "quantity": max(0, quantity),
        "reason": system_reason
    }

def _hold(narrative_reason: str) -> dict:
    return {
        "action": "HOLD",
        "symbol": "",
        "quantity": 0,
        "reason": narrative_reason
    }

def _safe_parse_time(time_str: str):
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return None