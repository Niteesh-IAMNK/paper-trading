"""
strategy.py
Production-ready Aggressive Momentum Scalping Strategy for NIFTY Weekly Options.

Core Idea:
- High-frequency intraday momentum scalping using confluence of VWAP + Breakout + RSI + EMA Momentum.
- Designed for 10-20 trades/day.
- Accepts slightly higher trade frequency in exchange for more opportunities.
- Robust risk controls + daily limits.
- Clean separation between indicators, signals, and position management.

Live Trading Note (Options):
- This class works on NIFTY spot/futures 1-min data for signals.
- On 'long' signal  → Buy nearest ATM/0.5-delta weekly Call option.
- On 'short' signal → Buy nearest ATM/0.5-delta weekly Put option.
- Use the bought option's LTP for trailing stop (recommended) or map underlying moves.
- Position sizing should be based on premium paid (see config).
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import List, Dict, Optional
import logging

from .config import StrategyConfig

logging.getLogger(__name__).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class NiftyAggressiveMomentumScalper:
    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.current_day = None

    # ==================== INDICATORS ====================
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # VWAP (reset daily)
        df["date"] = df.index.date
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

        # EMAs for momentum
        df["ema_fast"] = df["close"].ewm(span=self.config.ema_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.config.ema_slow, adjust=False).mean()

        # Breakout levels (Donchian style)
        df["hh"] = df["high"].rolling(self.config.breakout_period).max().shift(1)
        df["ll"] = df["low"].rolling(self.config.breakout_period).min().shift(1)

        # ATR
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(self.config.atr_period).mean()

        return df.dropna()

    # ==================== SIGNAL GENERATION ====================
    def _get_signal(self, row: pd.Series) -> Optional[str]:
        if any(pd.isna([row.get("vwap"), row.get("rsi"), row.get("ema_fast"), row.get("hh")])):
            return None

        long_score = sum([
            row["close"] > row["vwap"],
            row["rsi"] > 50,
            row["ema_fast"] > row["ema_slow"],
            row["close"] > row["hh"],
        ])

        short_score = sum([
            row["close"] < row["vwap"],
            row["rsi"] < 50,
            row["ema_fast"] < row["ema_slow"],
            row["close"] < row["ll"],
        ])

        if long_score >= self.config.min_score_long:
            return "long"
        if short_score >= self.config.min_score_short:
            return "short"
        return None

    def is_trading_time(self, ts: pd.Timestamp) -> bool:
        t = ts.time()
        return time.fromisoformat(self.config.trading_start) <= t <= time.fromisoformat(self.config.trading_end)

    # ==================== BACKTEST ENGINE ====================
    def backtest(self, df: pd.DataFrame) -> Dict:
        df = self.add_indicators(df)
        if len(df) < 50:
            return {"error": "Not enough data after indicator calculation"}

        position = 0
        entry_price = 0.0
        entry_idx = 0
        trailing_stop = 0.0
        trades = []
        equity = self.config.initial_capital
        equity_curve = [equity]

        for i in range(len(df)):
            row = df.iloc[i]
            ts = df.index[i]

            if not self.is_trading_time(ts):
                continue

            # Daily reset
            if self.current_day != ts.date():
                self.current_day = ts.date()
                self.trades_today = 0
                self.daily_pnl = 0.0

            signal = self._get_signal(row)

            # === Position Management ===
            if position != 0:
                exit_reason = None
                hold_minutes = (ts - df.index[entry_idx]).total_seconds() / 60

                if hold_minutes > self.config.max_hold_minutes:
                    exit_reason = "time_exit"
                elif position == 1:
                    new_trail = row["close"] - row["atr"] * self.config.trail_atr_mult
                    trailing_stop = max(trailing_stop, new_trail)
                    if row["close"] < trailing_stop:
                        exit_reason = "trailing_sl"
                elif position == -1:
                    new_trail = row["close"] + row["atr"] * self.config.trail_atr_mult
                    trailing_stop = min(trailing_stop, new_trail)
                    if row["close"] > trailing_stop:
                        exit_reason = "trailing_sl"
                elif (position == 1 and signal == "short") or (position == -1 and signal == "long"):
                    exit_reason = "signal_flip"

                if exit_reason:
                    exit_price = row["close"]
                    pnl = (exit_price - entry_price) * position * self.config.lot_size
                    equity += pnl
                    self.daily_pnl += pnl

                    trades.append({
                        "entry_time": str(df.index[entry_idx]),
                        "exit_time": str(ts),
                        "direction": "long" if position == 1 else "short",
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "pnl": round(pnl, 2),
                        "reason": exit_reason,
                        "hold_minutes": round(hold_minutes, 1),
                    })
                    position = 0
                    equity_curve.append(equity)

            # === New Entry ===
            if position == 0 and signal and self.trades_today < self.config.max_trades_per_day:
                daily_loss_pct = abs(self.daily_pnl) / equity * 100 if equity > 0 else 0
                if daily_loss_pct < self.config.daily_loss_limit_pct:
                    position = 1 if signal == "long" else -1
                    entry_price = row["close"]
                    entry_idx = i
                    trailing_stop = entry_price - position * row["atr"] * self.config.trail_atr_mult
                    self.trades_today += 1

        # Close any remaining position
        if position != 0 and len(df) > 0:
            last_row = df.iloc[-1]
            exit_price = last_row["close"]
            pnl = (exit_price - entry_price) * position * self.config.lot_size
            equity += pnl
            trades.append({
                "entry_time": str(df.index[entry_idx]),
                "exit_time": str(df.index[-1]),
                "direction": "long" if position == 1 else "short",
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "pnl": round(pnl, 2),
                "reason": "end_of_data",
                "hold_minutes": round((df.index[-1] - df.index[entry_idx]).total_seconds() / 60, 1),
            })
            equity_curve.append(equity)

        if not trades:
            return {"message": "No trades generated. Consider lowering min_score or breakout_period."}

        total_pnl = sum(t["pnl"] for t in trades)
        wins = [t for t in trades if t["pnl"] > 0]
        win_rate = len(wins) / len(trades) * 100
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return {
            "total_trades": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "avg_trade_pnl": round(total_pnl / len(trades), 2),
            "trades": trades,
            "equity_curve": equity_curve,
            "config": self.config.__dict__,
        }


# ==================== LIVE PAPER TRADING INTERFACE ====================

from collections import deque
from datetime import datetime

_LIVE_CONFIG = StrategyConfig()
_LIVE_STATE = {
    "nifty_history": deque(maxlen=60),
    "high_history": deque(maxlen=60),
    "low_history": deque(maxlen=60),
    "ema_fast": None,
    "ema_slow": None,
    "vwap_num": 0.0,
    "vwap_den": 0.0,
    "highest_option_price": None,
    "trades_today": 0,
    "current_date": None,
    "daily_pnl": 0.0,
}


def _hold(reason: str) -> dict:
    return {
        "action": "HOLD",
        "symbol": "",
        "quantity": 0,
        "reason": reason[:250],
    }


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value):
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _parse_time(snapshot: dict):
    value = snapshot.get("time")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _ema(previous, price, period):
    alpha = 2 / (period + 1)
    if previous is None:
        return price
    return previous + alpha * (price - previous)


def _rsi(prices):
    if len(prices) < _LIVE_CONFIG.rsi_period + 1:
        return None

    gains = []
    losses = []
    values = list(prices)

    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-_LIVE_CONFIG.rsi_period:]) / _LIVE_CONFIG.rsi_period
    avg_loss = sum(losses[-_LIVE_CONFIG.rsi_period:]) / _LIVE_CONFIG.rsi_period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _momentum_signal(nifty, rsi, ema_fast, ema_slow, hh, ll):
    if any(value is None for value in (nifty, rsi, ema_fast, ema_slow, hh, ll)):
        return None

    long_score = sum([
        nifty > _LIVE_STATE["vwap_num"] / max(_LIVE_STATE["vwap_den"], 1),
        rsi > 50,
        ema_fast > ema_slow,
        nifty > hh,
    ])

    short_score = sum([
        nifty < _LIVE_STATE["vwap_num"] / max(_LIVE_STATE["vwap_den"], 1),
        rsi < 50,
        ema_fast < ema_slow,
        nifty < ll,
    ])

    if long_score >= _LIVE_CONFIG.min_score_long:
        return "long"
    if short_score >= _LIVE_CONFIG.min_score_short:
        return "short"
    return None


def _calculate_quantity(cash, premium):
    if not cash or not premium or premium <= 0:
        return 0

    risk_capital = cash * (_LIVE_CONFIG.option_risk_per_trade_pct / 100.0)
    lots = int(risk_capital // (premium * _LIVE_CONFIG.lot_size))
    return max(0, lots * _LIVE_CONFIG.lot_size)


def generate_signal(snapshot: dict) -> dict:
    """
    Live paper-trading signal generator.

    Matches the public interface used by GPT and Gemini strategies.
    """
    try:
        if not isinstance(snapshot, dict):
            return _hold("Invalid snapshot")

        now = _parse_time(snapshot)
        nifty = _safe_float(snapshot.get("nifty"))
        if nifty is None or nifty <= 0:
            return _hold("Invalid NIFTY")

        if now and _LIVE_STATE["current_date"] != now.date():
            _LIVE_STATE["current_date"] = now.date()
            _LIVE_STATE["trades_today"] = 0
            _LIVE_STATE["daily_pnl"] = 0.0
            _LIVE_STATE["vwap_num"] = 0.0
            _LIVE_STATE["vwap_den"] = 0.0
            _LIVE_STATE["highest_option_price"] = None

        _LIVE_STATE["nifty_history"].append(nifty)
        _LIVE_STATE["high_history"].append(nifty)
        _LIVE_STATE["low_history"].append(nifty)
        _LIVE_STATE["vwap_num"] += nifty
        _LIVE_STATE["vwap_den"] += 1

        _LIVE_STATE["ema_fast"] = _ema(
            _LIVE_STATE["ema_fast"],
            nifty,
            _LIVE_CONFIG.ema_fast,
        )
        _LIVE_STATE["ema_slow"] = _ema(
            _LIVE_STATE["ema_slow"],
            nifty,
            _LIVE_CONFIG.ema_slow,
        )

        if now:
            current_time = now.strftime("%H:%M")
            if (
                current_time < _LIVE_CONFIG.trading_start
                or current_time > _LIVE_CONFIG.trading_end
            ):
                return _hold("Outside trading window")

        equity = _safe_float(snapshot.get("equity")) or 0.0
        if equity > 0:
            daily_loss_pct = abs(min(_LIVE_STATE["daily_pnl"], 0)) / equity * 100
            if daily_loss_pct >= _LIVE_CONFIG.daily_loss_limit_pct:
                return _hold("Daily loss limit reached")

        if _LIVE_STATE["trades_today"] >= _LIVE_CONFIG.max_trades_per_day:
            return _hold("Trade limit reached")

        if len(_LIVE_STATE["nifty_history"]) < _LIVE_CONFIG.breakout_period + 2:
            return _hold("Building indicators")

        rsi = _rsi(_LIVE_STATE["nifty_history"])
        hh = max(list(_LIVE_STATE["high_history"])[-_LIVE_CONFIG.breakout_period - 1:-1])
        ll = min(list(_LIVE_STATE["low_history"])[-_LIVE_CONFIG.breakout_period - 1:-1])

        if snapshot.get("has_position"):
            position = snapshot.get("position") or {}
            symbol = position.get("symbol")
            quantity = _safe_int(position.get("quantity"))
            entry = _safe_float(position.get("entry_price"))

            if not symbol or quantity <= 0 or entry is None:
                return _hold("Corrupt position")

            current = None
            if symbol == snapshot.get("ce_symbol"):
                current = _safe_float(snapshot.get("ce_price"))
            elif symbol == snapshot.get("pe_symbol"):
                current = _safe_float(snapshot.get("pe_price"))

            if current is None:
                return _hold("No option price")

            highest = _LIVE_STATE["highest_option_price"]
            if highest is None or current > highest:
                highest = current
                _LIVE_STATE["highest_option_price"] = highest

            pnl_pct = (current - entry) / entry
            trail_drop = highest * (1 - (_LIVE_CONFIG.trail_atr_mult / 100))

            if pnl_pct <= -0.08:
                reason = "Stop Loss"
            elif pnl_pct >= 0.12:
                reason = "Target Hit"
            elif current <= trail_drop:
                reason = "Trailing Stop"
            else:
                return _hold("Managing position")

            _LIVE_STATE["trades_today"] += 1
            return {
                "action": "SELL",
                "symbol": symbol,
                "quantity": quantity,
                "reason": reason,
            }

        signal = _momentum_signal(
            nifty,
            rsi,
            _LIVE_STATE["ema_fast"],
            _LIVE_STATE["ema_slow"],
            hh,
            ll,
        )

        if not signal:
            return _hold("No momentum setup")

        if signal == "long":
            symbol = snapshot.get("ce_symbol")
            premium = _safe_float(snapshot.get("ce_price"))
            reason = "Aggressive bullish momentum"
        else:
            symbol = snapshot.get("pe_symbol")
            premium = _safe_float(snapshot.get("pe_price"))
            reason = "Aggressive bearish momentum"

        if not symbol or premium is None or premium <= 0:
            return _hold("Invalid ATM option")

        quantity = _calculate_quantity(snapshot.get("cash"), premium)
        if quantity <= 0:
            return _hold("Insufficient cash")

        _LIVE_STATE["highest_option_price"] = premium
        _LIVE_STATE["trades_today"] += 1

        return {
            "action": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "reason": reason,
        }

    except Exception:
        return _hold("Internal protection")


# ==================== EXAMPLE USAGE ====================
if __name__ == "__main__":
    # Example: Load your 1-minute NIFTY data
    # df = pd.read_parquet("nifty_1min_2025.parquet")  # Must have columns: open, high, low, close, volume
    # df.index = pd.to_datetime(df.index)

    config = StrategyConfig(max_trades_per_day=15, trail_atr_mult=1.1, max_hold_minutes=20)
    strategy = NiftyAggressiveMomentumScalper(config)

    # results = strategy.backtest(df)
    # print(results["total_pnl"], results["win_rate"])

    print("Strategy class loaded successfully. Use with your 1-min NIFTY dataframe.")