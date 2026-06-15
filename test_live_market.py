from time import sleep
from shared.market_data import (
    refresh_indices,
    get_market
)

while True:

    refresh_indices()

    market = get_market()

    print(
        market["timestamp"],
        "NIFTY:",
        market["nifty"],
        "BANKNIFTY:",
        market["banknifty"]
    )

    sleep(5)