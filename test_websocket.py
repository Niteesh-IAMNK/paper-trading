from shared.websocket_feed import (
    MarketFeed
)

feed = MarketFeed(
    [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX"
    ]
)

feed.start()