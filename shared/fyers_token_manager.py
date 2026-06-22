import json
import time
import jwt
from pathlib import Path

TOKEN_FILE = Path(
    "fyers_token.json"
)


def load_tokens():
    """
    Load token file.
    """

    if not TOKEN_FILE.exists():
        return {}

    with open(
        TOKEN_FILE,
        "r"
    ) as f:

        return json.load(f)


def save_tokens(data):
    """
    Save token file.
    """

    with open(
        TOKEN_FILE,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
        )


def get_access_token():
    """
    Returns access token.
    """

    data = load_tokens()

    return data.get(
        "access_token"
    )


def get_refresh_token():
    """
    Returns refresh token.
    """

    data = load_tokens()

    return data.get(
        "refresh_token"
    )


def token_expired():
    """
    Returns True if access token
    is expired or about to expire
    in the next 5 minutes.
    """

    token = get_access_token()

    if not token:
        return True

    try:

        payload = jwt.decode(
            token,
            options={
                "verify_signature":
                    False
            }
        )

        exp = payload.get(
            "exp"
        )

        if not exp:
            return True

        return (
            time.time()
            >=
            exp - 300
        )

    except Exception:
        return True


def get_token_expiry():
    """
    Returns access token expiry
    timestamp.
    """

    token = get_access_token()

    if not token:
        return None

    try:

        payload = jwt.decode(
            token,
            options={
                "verify_signature":
                    False
            }
        )

        return payload.get(
            "exp"
        )

    except Exception:
        return None


def refresh_access_token():
    """
    Placeholder until FYERS
    refresh API is confirmed.
    """

    raise NotImplementedError(
        "FYERS refresh token API "
        "is not implemented yet."
    )


def get_valid_access_token():
    """
    Returns a valid access token.
    """

    if token_expired():

        refresh_access_token()

    return get_access_token()