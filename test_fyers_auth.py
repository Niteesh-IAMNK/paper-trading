from shared.fyers_auth import get_login_url

print(get_login_url())
from shared.fyers_auth import generate_access_token

auth_code = input(
    "Enter auth_code: "
).strip()

response = generate_access_token(
    auth_code
)

print(response)