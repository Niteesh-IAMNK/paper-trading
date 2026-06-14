from datetime import datetime
from copy import deepcopy


_latest_market = {
    "timestamp": None,
    "nifty": None,
    "banknifty": None,
    "symbols": {}
}


def update_index(
    *,
    nifty=None,
    banknifty=None
):
    """
    Update NIFTY and BANKNIFTY prices.
    """

    global _latest_market

    _latest_market["timestamp"] = datetime.utcnow()

    if nifty is not None:
        _latest_market["nifty"] = float(nifty)

    if banknifty is not None:
        _latest_market["banknifty"] = float(banknifty)


def update_symbol(
    symbol: str,
    ltp: float,
    volume: int = 0,
    oi: int = 0
):
    """
    Update a symbol price.
    Can be used for:
    - Options
    - Stocks
    - Indices
    """

    global _latest_market

    _latest_market["timestamp"] = datetime.utcnow()

    _latest_market["symbols"][symbol] = {
        "ltp": float(ltp),
        "volume": volume,
        "oi": oi,
        "updated_at": datetime.utcnow()
    }


def get_symbol(symbol: str):
    """
    Get latest data for a symbol.
    """

    return _latest_market["symbols"].get(symbol)


def get_ltp(symbol: str):
    """
    Get latest traded price.
    """

    data = get_symbol(symbol)

    if data is None:
        return None

    return data["ltp"]


def get_nifty():
    return _latest_market["nifty"]


def get_banknifty():
    return _latest_market["banknifty"]


def get_timestamp():
    return _latest_market["timestamp"]


def get_market_data():
    """
    Returns a safe copy.
    """

    return deepcopy(_latest_market)


def reset_market_data():
    """
    Used for tests and replay mode.
    """

    global _latest_market

    _latest_market = {
        "timestamp": None,
        "nifty": None,
        "banknifty": None,
        "symbols": {}
    }