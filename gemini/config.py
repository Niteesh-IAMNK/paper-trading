"""
Configuration parameters for the Alpha-Confluence Trend System.
Designed for high-reliability algorithmic options execution.
"""

# Strategy Identification
STRATEGY_NAME = "AlphaConfluenceOptions"

# Time Constraints (IST)
# 09:30 - Allow overnight volatility to settle and VWAP to anchor
TRADE_START_TIME = "09:30:00"
# 15:15 - Strict auto square-off to avoid closing volatility
AUTO_SQUARE_OFF_TIME = "15:15:00"

# Technical Indicator Parameters
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
VOLUME_SMA_PERIOD = 20
HISTORY_LIMIT = 200  # Safe buffer for calculating RSI and MACD cleanly

# Position Sizing & Capital Allocation
CAPITAL_ALLOCATION_PCT = 0.05     # 5% of available cash per trade (Conservative)
DEFAULT_LOT_SIZE = 25             # Default NIFTY lot size
MAX_LOTS_PER_TRADE = 5            # Cap on maximum lot exposure

# Risk Management & Trade Limits
MAX_DAILY_TRADES = 8              # System limit to prevent over-trading
MAX_DAILY_DRAWDOWN_PCT = 0.05     # Hard halt if 5% of daily capital is lost
STOP_LOSS_PCT = 0.15              # 15% hard stop on option premium
TAKE_PROFIT_PCT = 0.30            # 30% take profit on option premium
TRAIL_BREAKEVEN_PCT = 0.10        # Move SL to breakeven at 10% profit