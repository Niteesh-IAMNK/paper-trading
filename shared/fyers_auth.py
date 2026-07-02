import os

from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

load_dotenv()

CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")
FYERS_USER_ID = os.getenv("FYERS_USER_ID")
FYERS_PIN = os.getenv("FYERS_PIN")


def validate_auth_config() -> list[str]:
    """Return a list of missing or invalid auth configuration values."""
    errors: list[str] = []

    if not CLIENT_ID:
        errors.append("FYERS_CLIENT_ID is not set")
    if not SECRET_KEY:
        errors.append("FYERS_SECRET_KEY is not set")
    if not REDIRECT_URI:
        errors.append("FYERS_REDIRECT_URI is not set")
    if not FYERS_USER_ID:
        errors.append("FYERS_USER_ID is not set")
    if not FYERS_PIN:
        errors.append("FYERS_PIN is not set")
    elif len(FYERS_PIN) != 4 or not FYERS_PIN.isdigit():
        errors.append("FYERS_PIN must be a 4-digit numeric PIN")

    return errors


def get_login_url():
    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
    )

    return session.generate_authcode()


def generate_access_token(auth_code: str):
    """Exchange auth_code for access token."""
    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
    )

    session.set_token(auth_code)

    return session.generate_token()


def get_fyers():
    """
    Returns an authenticated FYERS client.

    Ensures a valid access token before returning. If the token is missing
    or expired, browser login runs automatically.
    """
    from shared.fyers_token_manager import ensure_valid_token

    access_token = ensure_valid_token()

    return fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=access_token,
        is_async=False,
    )
