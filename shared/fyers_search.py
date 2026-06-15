import os
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

load_dotenv()

CLIENT_ID = os.getenv(
    "FYERS_CLIENT_ID"
)

ACCESS_TOKEN = os.getenv(
    "FYERS_ACCESS_TOKEN"
)

fyers = fyersModel.FyersModel(
    client_id=CLIENT_ID,
    token=ACCESS_TOKEN,
    is_async=False
)


def search_symbol(
    text: str
):
    """
    Search symbols in FYERS.

    Example:
    search_symbol("NIFTY")
    search_symbol("23600 CE")
    """

    data = {
        "symbol": text
    }

    return fyers.search(data)