"""
gpt/config.py

Configuration for F&O Index Options trading strategy (long options only).
Conservative, capital-preservation focused, deterministic rules.
Suitable for paper trading on NSE Index Options with the shared engine.
"""

# ========================
# Underlying & Instrument Preference
# ========================
# Order in which underlyings are considered when selecting contracts.
UNDERLYING_PREFERENCE = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

# Strike step for ATM calculation (points)
NIFTY_STRIKE_STEP = 50
BANKNIFTY_STRIKE_STEP = 100
FINNIFTY_STRIKE_STEP = 50
MIDCPNIFTY_STRIKE_STEP = 25

# ========================
# Position Sizing (Conservative)
# ========================
LOTS_PER_TRADE = 1          # Fixed 1 lot - prioritizes capital preservation over aggression
MIN_PREMIUM_RS = 15         # Skip illiquid cheap options
MAX_PREMIUM_RS = 800        # Skip expensive deep ITM (lower leverage)

# ========================
# Strike Selection (Slightly OTM for better risk/reward)
# ========================
OTM_OFFSET_PCT = 0.006      # ~0.6% OTM strike (e.g. 150-200 points on NIFTY)
                            # Balances cost, probability, and leverage

# ========================
# Risk Management & Exits (Hard Rules)
# ========================
TP_MULTIPLIER = 1.8         # Take profit if premium reaches 1.8x entry price
SL_MULTIPLIER = 0.35        # Stop loss if premium falls to 35% of entry (cut ~65% loss)
MAX_LOSS_PER_TRADE_RS = 25000  # Absolute max loss per trade in Rs (overrides multiplier if larger move)
MAX_HOLD_MINUTES = 90       # Time stop - exit after 90 min regardless of P&L (theta protection)

# ========================
# Capital & Drawdown Protection
# ========================
CASH_BUFFER_RS = 50000      # Keep minimum cash buffer
MAX_DRAWDOWN_PCT = 0.04     # Pause new entries if equity drops >4% from running peak
MIN_EQUITY_TO_TRADE = 450000  # Safety floor

# ========================
# Trade Frequency Control
# ========================
COOLDOWN_MINUTES = 25       # Minimum gap between trade actions (entry or exit)
                            # Prevents over-trading and allows thesis to play out

# ========================
# Market Timing (IST)
# ========================
MARKET_OPEN_IST = "09:15:00"
MARKET_CLOSE_IST = "15:30:00"
AUTO_SQUARE_OFF_IST = "15:15:00"   # Start closing positions 15 min before close
NO_NEW_ENTRY_AFTER_IST = "14:45:00"  # No fresh BUY after this time

# ========================
# Bias & Signal Logic
# ========================
# Use dual MA on underlying index for directional bias
SHORT_MA_PERIOD = 8
LONG_MA_PERIOD = 18
# Bullish bias  -> BUY CALL (slightly OTM)
# Bearish bias -> BUY PUT  (slightly OTM)
# Neutral      -> HOLD (no trade)