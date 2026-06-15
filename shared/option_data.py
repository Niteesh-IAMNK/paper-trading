from .fyers_market import (
    get_quotes
)


def get_quote(
    symbol
):
    response = get_quotes(
        [symbol]
    )

    if response.get("s") != "ok":
        return None

    try:
        return response["d"][0]
    except:
        return None


def get_ltp(
    symbol
):
    quote = get_quote(
        symbol
    )

    if not quote:
        return None

    try:
        return quote["v"]["lp"]
    except:
        return None