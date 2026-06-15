from .fyers_auth import get_fyers

fyers = get_fyers()


def get_ltp(symbol):
    """
    Returns latest traded price.
    """

    if not symbol:
        return None

    response = fyers.quotes(
        {
            "symbols": symbol
        }
    )

    try:
        return (
            response["d"][0]
            ["v"]["lp"]
        )

    except Exception:
        return None