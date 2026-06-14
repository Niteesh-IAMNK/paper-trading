from copy import deepcopy

from .market_data import get_market_data
from .portfolio import has_open_position


def build_snapshot(portfolio):
    """
    Creates a market snapshot for an AI strategy.
    """

    market = get_market_data()

    snapshot = {
        "time": (
            market["timestamp"].isoformat()
            if market["timestamp"]
            else None
        ),

        "nifty": market["nifty"],
        "banknifty": market["banknifty"],

        "cash": portfolio.cash,
        "equity": portfolio.equity,

        "realized_pnl":
            portfolio.realized_pnl,

        "unrealized_pnl":
            portfolio.unrealized_pnl,

        "has_position":
            has_open_position(
                portfolio
            ),

        "position":
            None,

        "symbols":
            deepcopy(
                market["symbols"]
            )
    }

    if portfolio.position:
        snapshot["position"] = {
            "symbol":
                portfolio.position.symbol,

            "quantity":
                portfolio.position.quantity,

            "entry_price":
                portfolio.position.entry_price,

            "entry_time":
                portfolio.position
                .entry_time
                .isoformat()
        }

    return snapshot