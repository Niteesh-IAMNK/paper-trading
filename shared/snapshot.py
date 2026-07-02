from copy import deepcopy

from .market_data import get_market_data
from .option_chain import (
    get_atm_options,
    refresh_option_chain_if_strike_changed,
)
from .fyers_market import get_multiple_ltps
from .portfolio import has_open_position

_CYCLE_CONTEXT = None


def begin_snapshot_cycle() -> None:
    """Reset per-cycle shared snapshot data."""
    global _CYCLE_CONTEXT
    _CYCLE_CONTEXT = None


def get_shared_market_context(force_chain: bool = False) -> dict:
    """
    Build shared market context once per engine cycle.

    All strategies consume this cached context instead of calling FYERS
    independently.
    """
    global _CYCLE_CONTEXT

    if _CYCLE_CONTEXT is not None and not force_chain:
        return _CYCLE_CONTEXT

    market = get_market_data()
    refresh_option_chain_if_strike_changed(market.get("nifty"))
    options = get_atm_options(force=force_chain)

    atm_strike = None
    ce_symbol = None
    pe_symbol = None
    ce_price = None
    pe_price = None

    if options:
        atm_strike = options["strike"]
        ce_symbol = options["ce"]
        pe_symbol = options["pe"]

        quote_symbols = [
            symbol
            for symbol in (ce_symbol, pe_symbol)
            if symbol
        ]

        if quote_symbols:
            prices = get_multiple_ltps(quote_symbols)
            ce_price = prices.get(ce_symbol) if ce_symbol else None
            pe_price = prices.get(pe_symbol) if pe_symbol else None

    _CYCLE_CONTEXT = {
        "time": (
            market["timestamp"].isoformat()
            if market.get("timestamp")
            else None
        ),
        "nifty": market.get("nifty"),
        "banknifty": market.get("banknifty"),
        "atm_strike": atm_strike,
        "ce_symbol": ce_symbol,
        "pe_symbol": pe_symbol,
        "ce_price": ce_price,
        "pe_price": pe_price,
        "symbols": deepcopy(market.get("symbols", {})),
    }

    return _CYCLE_CONTEXT


def invalidate_market_snapshot_cache() -> None:
    """Force the next cycle to refresh shared market data."""
    global _CYCLE_CONTEXT
    _CYCLE_CONTEXT = None
    from .option_chain import invalidate_option_chain_cache
    from .fyers_market import invalidate_quotes_cache

    invalidate_option_chain_cache()
    invalidate_quotes_cache()


def build_snapshot(portfolio, shared_context: dict | None = None):
    """
    Creates a market snapshot for an AI strategy.
    """
    context = shared_context or get_shared_market_context()

    snapshot = {
        "time": context.get("time"),
        "nifty": context.get("nifty"),
        "banknifty": context.get("banknifty"),
        "atm_strike": context.get("atm_strike"),
        "ce_symbol": context.get("ce_symbol"),
        "pe_symbol": context.get("pe_symbol"),
        "ce_price": context.get("ce_price"),
        "pe_price": context.get("pe_price"),
        "cash": portfolio.cash,
        "equity": portfolio.equity,
        "realized_pnl": portfolio.realized_pnl,
        "unrealized_pnl": portfolio.unrealized_pnl,
        "has_position": has_open_position(portfolio),
        "position": None,
        "symbols": deepcopy(context.get("symbols", {})),
    }

    if portfolio.position:
        snapshot["position"] = {
            "symbol": portfolio.position.symbol,
            "quantity": portfolio.position.quantity,
            "entry_price": portfolio.position.entry_price,
            "entry_time": portfolio.position.entry_time.isoformat(),
        }

    return snapshot
