from .config import INITIAL_CAPITAL
from .models import Portfolio


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