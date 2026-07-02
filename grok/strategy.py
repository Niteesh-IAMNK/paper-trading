# strategy.py
"""
strategy.py
NIFTY Weekly Options Momentum Strategy (Standardized v3)

Objective: Maximize long-term compounded portfolio value over many weeks/months.
- High-quality confluence entries only (min 3/4 conditions).
- Dynamic lots: scales with current equity (compounding) + signal strength.
- Simple premium-based exits when in a position (cut losers early, trail winners).
- Engine handles: all timings, sessions, square-off, capital, risk validation, position tracking, execution, daily loss limits, counters, etc.
- Strategy returns ONLY action + lots (for BUY) + symbol + reason. No quantity, no validation, no duplication of global systems.

Trading instrument: NIFTY Weekly CE or PE only. Intraday.

This version strips all forbidden logic (market timings, trade counters, daily loss enforcement, quantity calc, lot size hardcoding, position state beyond minimal indicator history and simple premium exits).

Backtest is retained for development but uses local lot size for simulation only.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from .config import StrategyConfig

logging.getLogger(__name__).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class NiftyMomentumScalper:
    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()

    # ==================== BACKTEST (Development only) ====================
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = df.index.date

        # VWAP
        df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
        df["tpv"] = df["tp"] * df["volume"].fillna(0)
        df["cum_tpv"] = df.groupby("date")["tpv"].cumsum()
        df["cum_vol"] = df.groupby("date")["volume"].cumsum().replace(0, np.nan)
        df["vwap"] = df["cum_tpv"] / df["cum_vol"]

        # RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(self.config.rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.config.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        # EMAs
        df["ema_fast"] = df["close"].ewm(span=self.config.ema_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.config.ema_slow, adjust=False).mean()

        # Breakout (Donchian)
        df["hh"] = df["high"].rolling(self.config.breakout_period).max().shift(1)
        df["ll"] = df["low"].rolling(self.config.breakout_period).min().shift(1)

        return df.dropna()

    def _get_signal(self, row: pd.Series) -> Optional[str]:
        if any(pd.isna([row.get("vwap"), row.get("rsi"), row.get("ema_fast"), row.get("hh")])):
            return None

        long_score = sum([
            row["close"] > row["vwap"],
            row["rsi"] > 53,
            row["ema_fast"] > row["ema_slow"],
            row["close"] > row["hh"],
        ])

        short_score = sum([
            row["close"] < row["vwap"],
            row["rsi"] < 47,
            row["ema_fast"] < row["ema_slow"],
            row["close"] < row["ll"],
        ])

        if long_score >= self.config.min_score_long:
            return "long"
        if short_score >= self.config.min_score_short:
            return "short"
        return None

    def backtest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Backtest for development/validation only.
        Uses local lot size for P&L simulation (engine uses real current NSE lot size in live).
        """
        LOCAL_LOT_SIZE = 65  # Current NSE value for simulation only. Do not use in live path.
        df = self.add_indicators(df)
        if len(df) < 50:
            return {"error": "Insufficient data after indicators"}

        position = 0
        entry_price = 0.0
        entry_idx = 0
        trades = []
        equity = 500_000.0
        equity_curve = [equity]

        for i in range(len(df)):
            row = df.iloc[i]
            signal = self._get_signal(row)

            if position != 0:
                # Simple exit on opposite signal or end (backtest approximation)
                exit_now = False
                if (position == 1 and signal == "short") or (position == -1 and signal == "long"):
                    exit_now = True
                if i == len(df) - 1:
                    exit_now = True

                if exit_now:
                    exit_price = row["close"]
                    pnl = (exit_price - entry_price) * position * LOCAL_LOT_SIZE
                    equity += pnl
                    trades.append({
                        "entry_time": str(df.index[entry_idx]),
                        "exit_time": str(df.index[i]),
                        "direction": "long" if position == 1 else "short",
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "pnl": round(pnl, 2),
                    })
                    position = 0
                    equity_curve.append(equity)

            if position == 0 and signal:
                position = 1 if signal == "long" else -1
                entry_price = row["close"]
                entry_idx = i

        if not trades:
            return {"message": "No trades. Strategy is selective by design for long-term edge."}

        total_pnl = sum(t["pnl"] for t in trades)
        wins = sum(1 for t in trades if t["pnl"] > 0)
        win_rate = wins / len(trades) * 100
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return {
            "total_trades": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(pf, 2),
            "final_equity": round(equity, 2),
            "trades": trades,
            "note": "Backtest uses spot approximation + fixed lot for simulation. Live uses real option premiums + dynamic lots + engine risk controls."
        }

    # ==================== LIVE SIGNAL GENERATOR ====================
    # Minimal state only for indicators (deques) + daily vwap reset + simple premium trailing for exits.
    # No trade counters, no daily loss checks, no market time logic, no quantity calc, no lot size.

_LIVE_CONFIG = StrategyConfig()
_LIVE_STATE: Dict[str, Any] = {
    "nifty_history": [],
    "high_history": [],
    "low_history": [],
    "ema_fast": None,
    "ema_slow": None,
    "vwap_num": 0.0,
    "vwap_den": 0.0,
    "current_date": None,
    "highest_option_price": None,
}


def _safe_float(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _safe_int(v):
    try:
        return max(0, int(v)) if v is not None else 0
    except Exception:
        return 0


def _parse_time(snapshot: dict) -> Optional[datetime]:
    val = snapshot.get("time")
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def _ema(prev, price, period):
    if prev is None:
        return price
    alpha = 2.0 / (period + 1)
    return prev + alpha * (price - prev)


def _rsi(prices, period):
    if len(prices) < period + 1:
        return None
    vals = list(prices)
    gains = [max(vals[i] - vals[i-1], 0) for i in range(1, len(vals))]
    losses = [max(vals[i-1] - vals[i], 0) for i in range(1, len(vals))]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))


def _get_signal_and_score(nifty, rsi, ema_fast, ema_slow, hh, ll) -> tuple:
    if any(x is None for x in (nifty, rsi, ema_fast, ema_slow, hh, ll)):
        return None, 0

    vwap = _LIVE_STATE["vwap_num"] / max(_LIVE_STATE["vwap_den"], 1)

    long_score = sum([
        nifty > vwap,
        rsi > 53,
        ema_fast > ema_slow,
        nifty > hh,
    ])
    short_score = sum([
        nifty < vwap,
        rsi < 47,
        ema_fast < ema_slow,
        nifty < ll,
    ])

    if long_score >= _LIVE_CONFIG.min_score_long:
        return "long", long_score
    if short_score >= _LIVE_CONFIG.min_score_short:
        return "short", short_score
    return None, 0


def generate_signal(snapshot: dict) -> dict:
    """
    Returns trading decision only.
    Format:
      HOLD -> {"action": "HOLD", "reason": str}
      BUY  -> {"action": "BUY", "symbol": str, "lots": int, "reason": str, "confidence": float (optional)}
      SELL -> {"action": "SELL", "symbol": str, "reason": str}   # engine closes full position
    """
    try:
        if not isinstance(snapshot, dict):
            return {"action": "HOLD", "reason": "Invalid snapshot"}

        now = _parse_time(snapshot)
        nifty = _safe_float(snapshot.get("nifty"))
        if nifty is None or nifty <= 0:
            return {"action": "HOLD", "reason": "No valid NIFTY price"}

        # Daily reset for VWAP accumulator (indicator correctness only)
        if now and _LIVE_STATE["current_date"] != now.date():
            _LIVE_STATE["current_date"] = now.date()
            _LIVE_STATE["vwap_num"] = 0.0
            _LIVE_STATE["vwap_den"] = 0.0
            _LIVE_STATE["highest_option_price"] = None

        # Update indicator state
        _LIVE_STATE["nifty_history"].append(nifty)
        if len(_LIVE_STATE["nifty_history"]) > 60:
            _LIVE_STATE["nifty_history"].pop(0)
        _LIVE_STATE["high_history"].append(nifty)
        if len(_LIVE_STATE["high_history"]) > 60:
            _LIVE_STATE["high_history"].pop(0)
        _LIVE_STATE["low_history"].append(nifty)
        if len(_LIVE_STATE["low_history"]) > 60:
            _LIVE_STATE["low_history"].pop(0)

        _LIVE_STATE["vwap_num"] += nifty
        _LIVE_STATE["vwap_den"] += 1

        _LIVE_STATE["ema_fast"] = _ema(_LIVE_STATE["ema_fast"], nifty, _LIVE_CONFIG.ema_fast)
        _LIVE_STATE["ema_slow"] = _ema(_LIVE_STATE["ema_slow"], nifty, _LIVE_CONFIG.ema_slow)

        # If engine reports we already have a position, decide simple premium-based exit or hold
        if snapshot.get("has_position"):
            pos = snapshot.get("position") or {}
            symbol = pos.get("symbol")
            entry = _safe_float(pos.get("entry_price"))
            current = None

            if symbol == snapshot.get("ce_symbol"):
                current = _safe_float(snapshot.get("ce_price"))
            elif symbol == snapshot.get("pe_symbol"):
                current = _safe_float(snapshot.get("pe_price"))

            if current is None or entry is None or current <= 0:
                return {"action": "HOLD", "reason": "Position data incomplete"}

            # Update peak for trailing
            if _LIVE_STATE["highest_option_price"] is None or current > _LIVE_STATE["highest_option_price"]:
                _LIVE_STATE["highest_option_price"] = current

            pnl_pct = (current - entry) / entry * 100.0
            highest = _LIVE_STATE["highest_option_price"]

            # Premium-based exits only (no time, no counters)
            if pnl_pct <= -_LIVE_CONFIG.option_sl_pct:
                _LIVE_STATE["highest_option_price"] = None
                return {"action": "SELL", "symbol": symbol, "reason": f"SL hit ({pnl_pct:.1f}%)"}
            if pnl_pct >= _LIVE_CONFIG.option_target_pct:
                _LIVE_STATE["highest_option_price"] = None
                return {"action": "SELL", "symbol": symbol, "reason": f"Target hit ({pnl_pct:.1f}%)"}

            trail_level = highest * (1 - _LIVE_CONFIG.option_trail_pct / 100.0)
            if current <= trail_level:
                _LIVE_STATE["highest_option_price"] = None
                return {"action": "SELL", "symbol": symbol, "reason": f"Trailing stop ({_LIVE_CONFIG.option_trail_pct}% from peak)"}

            return {"action": "HOLD", "reason": f"Managing | PnL {pnl_pct:.1f}%"}

        # No position: look for high-quality entry
        if len(_LIVE_STATE["nifty_history"]) < _LIVE_CONFIG.breakout_period + 2:
            return {"action": "HOLD", "reason": "Warming up indicators"}

        rsi = _rsi(_LIVE_STATE["nifty_history"], _LIVE_CONFIG.rsi_period)
        hh = max(_LIVE_STATE["high_history"][-_LIVE_CONFIG.breakout_period-1:-1]) if len(_LIVE_STATE["high_history"]) > _LIVE_CONFIG.breakout_period else None
        ll = min(_LIVE_STATE["low_history"][-_LIVE_CONFIG.breakout_period-1:-1]) if len(_LIVE_STATE["low_history"]) > _LIVE_CONFIG.breakout_period else None

        signal, score = _get_signal_and_score(nifty, rsi, _LIVE_STATE["ema_fast"], _LIVE_STATE["ema_slow"], hh, ll)

        if not signal:
            return {"action": "HOLD", "reason": "No 3+ confluence momentum setup"}

        # Choose option
        if signal == "long":
            symbol = snapshot.get("ce_symbol")
            premium = _safe_float(snapshot.get("ce_price"))
        else:
            symbol = snapshot.get("pe_symbol")
            premium = _safe_float(snapshot.get("pe_price"))

        if not symbol or premium is None or premium <= 0:
            return {"action": "HOLD", "reason": "No valid option premium/symbol"}

        # Dynamic lots: scale with equity (for compounding) + signal strength
        equity = _safe_float(snapshot.get("equity")) or 500_000.0
        scale = max(0.4, min(4.0, equity / 500_000.0))
        extra = max(0, score - _LIVE_CONFIG.min_score_long)
        lots = int((_LIVE_CONFIG.base_lots + extra * _LIVE_CONFIG.lots_per_extra_confluence) * scale)
        lots = max(1, min(_LIVE_CONFIG.max_lots, lots))

        _LIVE_STATE["highest_option_price"] = premium

        confidence = round(min(0.95, 0.6 + (score - 2) * 0.12), 2)

        return {
            "action": "BUY",
            "symbol": symbol,
            "lots": lots,
            "reason": f"{signal.upper()} momentum (score {score}/4) | equity_scale {scale:.2f}x",
            "confidence": confidence
        }

    except Exception as e:
        return {"action": "HOLD", "reason": f"Protection: {str(e)[:80]}"}


# Example usage (development)
if __name__ == "__main__":
    print("Standardized momentum strategy loaded.")
    print("Live generate_signal ready. Returns BUY/SELL/HOLD + lots (BUY) + symbol + reason.")
    print("Backtest available for offline validation.")