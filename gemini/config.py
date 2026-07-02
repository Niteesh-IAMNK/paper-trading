"""
Configuration parameters for the Alpha-Confluence Trend System.
Optimised purely for geometric portfolio compounding and momentum capture.
"""

# Strategy Identification
STRATEGY_NAME = "AlphaConfluenceGrowth"

# Technical Indicator Parameters
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
HISTORY_LIMIT = 200

# Position Sizing Heuristics
# Represents the baseline equity required per lot. 
# Example: 5,00,000 equity // 50,000 = 10 base lots. 
# The engine will validate cash; this just sets the geometric scaling curve.
EQUITY_PER_LOT_TIER = 50000 

# Risk & Trade Management
STOP_LOSS_PCT = 0.20              # 20% hard stop on option premium
TRAIL_ACTIVATION_PCT = 0.30       # Activate trailing stop after 30% profit is reached
TRAIL_PULLBACK_PCT = 0.15         # Trail by 15% from the highest premium reached
TRAIL_TIGHTEN_PCT = 0.10          # Tighten trail to 10% once profit exceeds 60%