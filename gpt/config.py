# config.py

"""
Conservative Institutional-Style ATM NIFTY Weekly Options Strategy
Focus:
1. Capital Preservation
2. Risk-Adjusted Returns
3. Low Drawdown
4. Low Trading Frequency (2-5 trades/day)
"""

# Capital Management
INITIAL_CAPITAL = 500_000
MAX_CAPITAL_PER_TRADE = 0.10  # Deploy only 10% of cash
LOT_SIZE = 75                 # Update if NSE revises

# Trading Window
ANALYSIS_START = "09:15:00"
TRADING_START = "10:30:00"
NO_NEW_ENTRY_AFTER = "14:45:00"
AUTO_SQUARE_OFF = "15:20:00"

# Indicators
FAST_EMA = 9
SLOW_EMA = 21
RSI_PERIOD = 14
MOMENTUM_LOOKBACK = 5

# Entry Filters
RSI_BULL_MIN = 55
RSI_BULL_MAX = 70
RSI_BEAR_MIN = 30
RSI_BEAR_MAX = 45

MIN_MOMENTUM = 0.0025  # 0.25%
MIN_EMA_SEPARATION = 0.001  # 0.10%

# No Trade Zone
NO_TRADE_RSI_LOW = 45
NO_TRADE_RSI_HIGH = 55
LUNCH_START = "11:45:00"
LUNCH_END = "12:30:00"

# Risk Management
STOP_LOSS_PCT = 0.25
TARGET_PCT = 0.40
TRAILING_STOP_PCT = 0.15

# Trading Controls
COOLDOWN_SECONDS = 300
MAX_TRADES_PER_DAY = 5
MAX_CONSECUTIVE_LOSSES = 3
MAX_DAILY_DRAWDOWN_PCT = 0.05

# History
MAX_HISTORY = 500