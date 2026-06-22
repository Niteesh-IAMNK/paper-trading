from shared.nse_session import (
    refresh_session
)

session = refresh_session()

response = session.get(
    "https://www.nseindia.com"
)

print("Status:", response.status_code)
print("Cookies:", session.cookies.get_dict())
print("Length:", len(response.text))