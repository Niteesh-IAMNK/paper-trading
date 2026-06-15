from shared.fyers_market import (
    get_ltp,
    get_multiple_ltps
)

print()

print(
    "NIFTY:",
    get_ltp(
        "NSE:NIFTY50-INDEX"
    )
)

print(
    "BANKNIFTY:",
    get_ltp(
        "NSE:NIFTYBANK-INDEX"
    )
)

print()

print(
    get_multiple_ltps(
        [
            "NSE:NIFTY50-INDEX",
            "NSE:NIFTYBANK-INDEX"
        ]
    )
)