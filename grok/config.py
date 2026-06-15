"""
config.py
Central configuration for the Aggressive NIFTY Weekly Options Momentum Scalper.
Edit these values to control aggressiveness vs robustness.
"""

from dataclasses import dataclass
from datetime import time


@dataclass
class StrategyConfig:
    # ===================== GENERAL =====================
    initial_capital: float = 500_000.0          # Starting capital for backtesting
    lot_size: int = 25                          # NIFTY lot size (standard)

    # ===================== INDICATORS =====================
    rsi_period: int = 14
    ema_fast: int = 9                           # Fast EMA for momentum
    ema_slow: int = 21                          # Slow EMA for momentum
    breakout_period: int = 12                   # Shorter = more aggressive breakouts
    atr_period: int = 14

    # ===================== SIGNAL LOGIC (AGGRESSIVE) =====================
    min_score_long: int = 2                     # Enter long if ≥ N conditions true (out of 4)
    min_score_short: int = 2                    # Enter short if ≥ N conditions true

    # ===================== RISK & EXIT MANAGEMENT =====================
    trail_atr_mult: float = 1.2                 # ATR multiplier for trailing stop
    max_hold_minutes: int = 25                  # Hard time-based exit (theta protection)
    max_trades_per_day: int = 15                # Hard cap on trade frequency
    daily_loss_limit_pct: float = 2.0           # Stop trading for the day if loss exceeds this %

    # ===================== TRADING HOURS (IST) =====================
    trading_start: str = "09:15"
    trading_end: str = "15:00"

    # ===================== OPTIONS SPECIFIC (for live) =====================
    # These are used only as guidance in live execution layer
    option_risk_per_trade_pct: float = 0.5      # Risk 0.5% of capital per trade on premium
    preferred_delta: float = 0.50               # Target ~ATM options