from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime


@dataclass
class Trade:
    ai_name: str
    symbol: str
    action: str
    quantity: int
    price: float
    timestamp: datetime
    pnl: float = 0.0
    reason: str = ""


@dataclass
class Portfolio:
    ai_name: str
    cash: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity: float = 0.0
    position: Optional[Position] = None


@dataclass
class Snapshot:
    time: str
    nifty: float
    banknifty: float
    positions: list
    cash: float