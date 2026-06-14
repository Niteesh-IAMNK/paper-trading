from .config import MAX_POSITIONS
from .portfolio import has_open_position


def can_buy(
    portfolio,
    quantity: int,
    price: float
):
    """
    Check if a BUY can be executed.
    """

    if has_open_position(portfolio):
        return (
            False,
            "Position already open."
        )

    cost = quantity * price

    if cost > portfolio.cash:
        return (
            False,
            "Insufficient funds."
        )

    return (
        True,
        "BUY allowed."
    )


def can_sell(portfolio):
    """
    Check if a SELL can be executed.
    """

    if not has_open_position(portfolio):
        return (
            False,
            "No open position."
        )

    return (
        True,
        "SELL allowed."
    )


def open_positions_count(
    portfolio
):
    """
    Returns number of open positions.
    """

    return (
        1
        if portfolio.position
        else 0
    )


def has_capacity(
    portfolio
):
    """
    Checks MAX_POSITIONS.
    """

    return (
        open_positions_count(
            portfolio
        ) < MAX_POSITIONS
    )