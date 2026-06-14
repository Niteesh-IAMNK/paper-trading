"""
Configuration parameters for the F&O Derivative Trading Strategy.
Designed for high-reliability execution on long-running servers.
"""

# Strategy Identification
STRATEGY_NAME = "AlphaDerivatives"

# Trading Target Configuration
# Supported base underlyings: "nifty", "banknifty"
BASE_UNDERLYING = "nifty" 
SYMBOL_FILTER_KEYWORD = "NIFTY"

# Technical Indicator Parameters
SHORT_WINDOW = 9
LONG_WINDOW = 21

# Position Sizing & Capital Allocation
MAX_LOTS_PER_TRADE = 2            # Conservative risk limitation
CAPITAL_RESERVE_PCT = 0.10        # Keep 10% cash cushion for safety

# Risk Management Thresholds
STOP_LOSS_PCT = 0.15              # 15% stop loss on option/future premium
TAKE_PROFIT_PCT = 0.30            # 30% take profit on option/future premium
MAX_DAILY_DRAWDOWN_PCT = 0.05     # 5% maximum capital drawdown per day

# Time-based Execution Constraints (IST)
AUTO_SQUARE_OFF_TIME = "15:15:00" # Square off open positions before market close
COOLDOWN_PERIOD_SECONDS = 300     # 5 minutes minimal delay between successive trades