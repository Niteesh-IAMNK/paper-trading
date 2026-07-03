from datetime import datetime

from .config import INITIAL_CAPITAL
from .database import get_portfolio, get_position, save_portfolio
from .models import Portfolio, Position


def load_portfolio(ai_name: str) -> Portfolio:
    """
    Load portfolio state from the database, or create and persist a new one.
    """
    row = get_portfolio(ai_name)
    if row is None:
        portfolio = create_portfolio(ai_name)
        save_portfolio(portfolio)
        return portfolio

    portfolio = Portfolio(
        ai_name=ai_name,
        cash=row["cash"],
        realized_pnl=row["realized_pnl"],
        unrealized_pnl=row["unrealized_pnl"],
        equity=row["equity"],
        position=None,
    )

    position_row = get_position(ai_name)
    if position_row is not None:
        portfolio.position = Position(
            symbol=position_row["symbol"],
            quantity=position_row["quantity"],
            entry_price=position_row["entry_price"],
            entry_time=datetime.fromisoformat(position_row["entry_time"]),
        )

    return portfolio


def create_portfolio(ai_name: str) -> Portfolio:
    """
    Create a new portfolio for an AI.
    """
    return Portfolio(
        ai_name=ai_name,
        cash=INITIAL_CAPITAL,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        equity=INITIAL_CAPITAL,
        position=None
    )


def get_equity(portfolio: Portfolio) -> float:
    """
    Returns current portfolio equity.
    """
    return (
        portfolio.cash +
        portfolio.unrealized_pnl
    )


def update_equity(portfolio: Portfolio) -> float:
    """
    Updates and returns portfolio equity.
    """
    portfolio.equity = get_equity(portfolio)
    return portfolio.equity


def reset_portfolio(portfolio: Portfolio) -> Portfolio:
    """
    Reset portfolio back to initial state.
    """
    portfolio.cash = INITIAL_CAPITAL
    portfolio.realized_pnl = 0.0
    portfolio.unrealized_pnl = 0.0
    portfolio.equity = INITIAL_CAPITAL
    portfolio.position = None

    return portfolio


def has_open_position(portfolio: Portfolio) -> bool:
    """
    Returns True if an open position exists.
    """
    return portfolio.position is not None