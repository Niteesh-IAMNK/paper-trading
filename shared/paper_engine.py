from datetime import datetime

from .models import Position, Trade
from .portfolio import (
    has_open_position,
    update_equity
)
from .database import (
    save_portfolio,
    save_position,
    clear_position,
    save_trade
)
from .config import LOT_SIZE
from .lot_sizing import validate_buy_quantity


def buy(
    portfolio,
    symbol: str,
    quantity: int,
    price: float,
    reason: str = ""
):
    """
    Open a new position.

    Returns:
        (success, message, trade)
    """

    if has_open_position(portfolio):
        return False, "Position already open.", None

    valid, validation_message = validate_buy_quantity(quantity)
    if not valid:
        return False, validation_message, None

    cost = quantity * price

    if cost > portfolio.cash:
        return False, "Insufficient funds.", None

    portfolio.cash -= cost

    portfolio.position = Position(
        symbol=symbol,
        quantity=quantity,
        entry_price=price,
        entry_time=datetime.utcnow()
    )

    update_equity(portfolio)

    trade = Trade(
        ai_name=portfolio.ai_name,
        symbol=symbol,
        action="BUY",
        quantity=quantity,
        price=price,
        timestamp=datetime.utcnow(),
        pnl=0.0,
        reason=reason
    )

    # Save to database
    save_position(
        portfolio.ai_name,
        portfolio.position
    )

    save_trade(trade)
    save_portfolio(portfolio)

    return True, "BUY executed.", trade


def sell(
    portfolio,
    price: float,
    reason: str = ""
):
    """
    Close the existing position.

    Returns:
        (success, message, trade)
    """

    if not has_open_position(portfolio):
        return False, "No open position.", None

    position = portfolio.position

    sale_value = position.quantity * price
    cost = position.quantity * position.entry_price

    pnl = sale_value - cost

    portfolio.cash += sale_value
    portfolio.realized_pnl += pnl
    portfolio.unrealized_pnl = 0
    portfolio.position = None

    update_equity(portfolio)

    trade = Trade(
        ai_name=portfolio.ai_name,
        symbol=position.symbol,
        action="SELL",
        quantity=position.quantity,
        price=price,
        timestamp=datetime.utcnow(),
        pnl=round(pnl, 2),
        reason=reason
    )

    # Save to database
    clear_position(portfolio.ai_name)

    save_trade(trade)
    save_portfolio(portfolio)

    return True, "SELL executed.", trade


def mark_to_market(
    portfolio,
    current_price: float
):
    """
    Calculate unrealized P&L.
    """

    if not has_open_position(portfolio):
        portfolio.unrealized_pnl = 0
        update_equity(portfolio)
        return 0

    position = portfolio.position

    pnl = (
        current_price -
        position.entry_price
    ) * position.quantity

    portfolio.unrealized_pnl = round(
        pnl,
        2
    )

    update_equity(portfolio)

    return portfolio.unrealized_pnl