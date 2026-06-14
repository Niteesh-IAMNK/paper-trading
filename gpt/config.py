"""
Conservative F&O intraday strategy configuration.
Designed for long-running paper trading systems.
"""

INITIAL_CAPITAL = 500_000
MAX_POSITIONS = 1

# Capital preservation
MAX_CAPITAL_USAGE = 0.20        # use at most 20% of cash
MAX_DAILY_DRAWDOWN = 0.05       # stop trading after 5% equity loss
MAX_CONSECUTIVE_LOSSES = 3

# Risk management
STOP_LOSS_PCT = 0.15            # 15%
TAKE_PROFIT_PCT = 0.20          # 20%
TRAILING_STOP_PCT = 0.10        # 10%

# Trading frequency controls
COOLDOWN_SECONDS = 300          # 5 minutes
MIN_OBSERVATIONS = 5

# Auto square-off
AUTO_SQUARE_OFF_TIME = "15:20:00"

# Momentum thresholds
ENTRY_MOMENTUM = 0.003          # 0.30%
EXIT_MOMENTUM = -0.002          # -0.20%

# History controls
MAX_HISTORY_SIZE = 300