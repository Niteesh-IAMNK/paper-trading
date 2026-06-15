from shared.fyers_market import get_quotes

response = get_quotes(
    [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX"
    ]
)

print(response)