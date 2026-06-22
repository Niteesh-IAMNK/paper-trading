from shared.fyers_auth import (
    get_fyers
)

fyers = get_fyers()

print(
    fyers.get_profile()
)