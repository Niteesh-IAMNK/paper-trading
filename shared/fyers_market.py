import os
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

load_dotenv()

CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN")

fyers = fyersModel.FyersModel(
    client_id=CLIENT_ID,
    token=ACCESS_TOKEN,
    is_async=False
)


def get_quotes(symbols: list):
    """
    Get live quotes from FYERS.

    Example:
    [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX"
    ]
    """

    data = {
        "symbols": ",".join(symbols)
    }

    return fyers.quotes(data)


def get_ltp(symbol: str):
    """
    Returns LTP of one symbol.
    """

    response = get_quotes([symbol])

    if response.get("s") != "ok":
        return None

    try:
        return response["d"][0]["v"]["lp"]
    except Exception:
        return None


def get_multiple_ltps(symbols: list):
    """
    Returns:
    {
        symbol: ltp
    }
    """

    result = {}

    response = get_quotes(symbols)

    if response.get("s") != "ok":
        return result

    try:
        for item in response["d"]:
            symbol = item["n"]
            ltp = item["v"]["lp"]
            result[symbol] = ltp
    except Exception:
        pass

    return result