from shared.fyers_token_manager import (
    load_tokens,
    get_access_token,
    get_refresh_token,
    token_expired,
    get_token_expiry
)

print(
    "Token File:"
)

print(
    load_tokens()
)

print(
    "\nAccess Token:"
)

print(
    get_access_token()[:40]
)

print(
    "\nRefresh Token:"
)

print(
    get_refresh_token()[:40]
)

print(
    "\nExpired:"
)

print(
    token_expired()
)

print(
    "\nExpiry Timestamp:"
)

print(
    get_token_expiry()
)