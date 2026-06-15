from copy import deepcopy

from .market_data import (
    get_market_data
)

from .portfolio import (
    has_open_position
)

from .option_chain import (
    get_atm_options
)

from .option_quotes import (
    get_ltp
)


def build_snapshot(portfolio):
    """
    Creates a market snapshot
    for an AI strategy.
    """

    market = get_market_data()

    options = get_atm_options()

    atm_strike = None
    ce_symbol = None
    pe_symbol = None
    ce_price = None
    pe_price = None

    if options:

        atm_strike = (
            options["strike"]
        )

        ce_symbol = (
            options["ce"]
        )

        pe_symbol = (
            options["pe"]
        )

        ce_price = get_ltp(
            ce_symbol
        )

        pe_price = get_ltp(
            pe_symbol
        )

    snapshot = {
        "time": (
            market["timestamp"].isoformat()
            if market["timestamp"]
            else None
        ),

        "nifty":
            market["nifty"],

        "banknifty":
            market["banknifty"],

        "atm_strike":
            atm_strike,

        "ce_symbol":
            ce_symbol,

        "pe_symbol":
            pe_symbol,

        "ce_price":
            ce_price,

        "pe_price":
            pe_price,

        "cash":
            portfolio.cash,

        "equity":
            portfolio.equity,

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