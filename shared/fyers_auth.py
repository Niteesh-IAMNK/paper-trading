import os

from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

load_dotenv()

CLIENT_ID = os.getenv(
    "FYERS_CLIENT_ID"
)

SECRET_KEY = os.getenv(
    "FYERS_SECRET_KEY"
)

REDIRECT_URI = os.getenv(
    "FYERS_REDIRECT_URI"
)


def get_login_url():

    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )

    return session.generate_authcode()


def generate_access_token(
    auth_code: str
):
    """
    Exchange auth_code
    for access token.
    """

    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )

    session.set_token(
        auth_code
    )

    return session.generate_token()


def get_fyers():
    """
    Returns authenticated
    FYERS client.
    """

    from auth_helper import ensure_valid_token

    access_token = ensure_valid_token()

    return fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=access_token,
        is_async=False
    )