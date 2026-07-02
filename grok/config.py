# config.py
"""
config.py
Minimal configuration for NIFTY Weekly Options momentum strategy.

Only values that genuinely need to be tunable for long-term portfolio growth are here.
The engine handles all session, risk, capital, execution, and position logic.
Strategy only decides entries (direction + lots) and simple premium-based exits.
"""

from dataclasses import dataclass


@dataclass
class StrategyConfig:
    # Indicator parameters (core to signal quality)
    rsi_period: int = 14
    ema_fast: int = 9
    ema_slow: int = 21
    breakout_period: int = 12          # Donchian breakout lookback

    # Signal quality threshold (higher = fewer but cleaner trades for compounding)
    min_score_long: int = 3
    min_score_short: int = 3

    # Position sizing (scaled by signal strength + current equity)
    base_lots: int = 2                 # Starting lots at ~₹5L equity on minimum valid signal
    lots_per_extra_confluence: int = 2 # Aggressive scaling on very strong setups (4/4)
    max_lots: int = 15                 # Safety cap even on hot streaks / large equity

    # Simple premium-based exit rules for when in position (protects compounding)
    option_sl_pct: float = 18.0        # Exit losing option position early
    option_target_pct: float = 35.0    # Lock in gains on momentum bursts
    option_trail_pct: float = 12.0     # Trail winners; exit on pullback from peak premium