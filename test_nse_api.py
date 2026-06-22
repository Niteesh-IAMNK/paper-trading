from shared.nse_session import (
    refresh_session
)

session = refresh_session()

url = (
    "https://www.nseindia.com/api/option-chain-indices"
    "?symbol=NIFTY"
)

response = session.get(
    url,
    timeout=10
)

print(
    "Status:",
    response.status_code
)

print(
    response.text[:300]
)