import os

from dotenv import load_dotenv
from fyers_apiv3.FyersWebsocket import data_ws

from shared.market_data import (
    MARKET
)

load_dotenv()

CLIENT_ID = os.getenv(
    "FYERS_CLIENT_ID"
)

from shared.fyers_token_manager import (
    get_access_token
)

access_token = (
    get_access_token()
)

ACCESS_TOKEN = (
    f"{CLIENT_ID}:{TOKEN}"
)


class MarketFeed:

    def __init__(
        self,
        symbols
    ):
        self.symbols = symbols
        self.socket = None

    def on_message(
        self,
        message
    ):
        symbol = message.get(
            "symbol"
        )

        ltp = message.get(
            "ltp"
        )

        if not symbol:
            return

        MARKET["symbols"][symbol] = {
            "ltp": ltp,
            "updated_at": message.get(
                "exch_feed_time"
            )
        }

        print(
            symbol,
            ltp
        )

    def on_error(
        self,
        message
    ):
        ...

    def on_close(
        self,
        message
    ):
        print(
            "WS Closed:",
            message
        )

    def on_open(self):

        self.socket.subscribe(
            symbols=self.symbols,
            data_type="SymbolUpdate"
        )

        self.socket.keep_running()

    def start(self):

        self.socket = (
            data_ws.FyersDataSocket(
                access_token=ACCESS_TOKEN,
                log_path="",
                litemode=False,
                write_to_file=False,
                reconnect=True,
                on_connect=self.on_open,
                on_close=self.on_close,
                on_error=self.on_error,
                on_message=self.on_message
            )
        )

        self.socket.connect()