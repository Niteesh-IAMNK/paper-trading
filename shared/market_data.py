from datetime import datetime
from .fyers_market import get_multiple_ltps

MARKET = {
    "timestamp": None,
    "nifty": None,
    "banknifty": None,
    "symbols": {}
}


def refresh_indices():
    """
    Pull latest index prices from FYERS.
    """

    prices = get_multiple_ltps(
        [
            "NSE:NIFTY50-INDEX",
            "NSE:NIFTYBANK-INDEX"
        ]
    )

    MARKET["timestamp"] = datetime.utcnow()

    MARKET["nifty"] = prices.get(
        "NSE:NIFTY50-INDEX"
    )

    MARKET["banknifty"] = prices.get(
        "NSE:NIFTYBANK-INDEX"
    )

    return MARKET


def get_nifty():
    return MARKET["nifty"]


def get_banknifty():
    return MARKET["banknifty"]


def get_market():
    return MARKET

def get_market_data():
    """
    Backward compatibility for older modules.
    """
    return get_market()