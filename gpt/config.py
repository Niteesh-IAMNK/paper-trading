"""
Pure decision configuration for the GPT NIFTY weekly-options strategy.

The trading engine owns market sessions, portfolio checks, lot-size conversion,
execution, position management, and risk enforcement. These values only shape
the strategy's directional edge model and requested lot count.
"""

# Indicator memory
MAX_HISTORY = 260
FAST_EMA = 8
MID_EMA = 21
SLOW_EMA = 55
RSI_PERIOD = 14
ATR_PERIOD = 14
BREAKOUT_LOOKBACK = 24
MOMENTUM_LOOKBACK = 9
OPTION_MOMENTUM_LOOKBACK = 4

# Edge filters
MIN_EDGE_SCORE = 3.05
MIN_ABS_MOMENTUM = 0.0016
MIN_EMA_SPREAD = 0.00055
MIN_ATR_PCT = 0.00018
MAX_ATR_PCT = 0.0075
OPTION_CONFIRMATION_MOVE = 0.018
OPTION_MIN_PREMIUM = 15

# Compounding-aware lot intent
REFERENCE_EQUITY = 500_000
BASE_LOTS = 2
MAX_LOTS = 300
MEDIUM_EDGE_MULTIPLIER = 1.7
HIGH_EDGE_MULTIPLIER = 2.9
EXTREME_EDGE_MULTIPLIER = 4.6
