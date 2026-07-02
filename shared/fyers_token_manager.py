import json
import time

import jwt
from fyers_apiv3 import fyersModel
from pathlib import Path

from shared.fyers_auth import (
    CLIENT_ID,
    generate_access_token,
    get_login_url,
    validate_auth_config,
)
from shared.fyers_browser import BrowserLoginError, run_browser_login
from shared.fyers_logger import log_error, log_info, log_warning

TOKEN_FILE = Path("fyers_token.json")


class TokenRenewalError(Exception):
    """Raised when token renewal or verification fails."""


def load_tokens():
    """Load token file."""
    if not TOKEN_FILE.exists():
        return {}

    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def save_tokens(data):
    """Save token file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_access_token():
    """Returns access token."""
    data = load_tokens()
    return data.get("access_token")


def get_refresh_token():
    """Returns refresh token."""
    data = load_tokens()
    return data.get("refresh_token")


def token_expired():
    """
    Returns True if access token is expired or about to expire
    in the next 5 minutes.
    """
    token = get_access_token()

    if not token:
        return True

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        exp = payload.get("exp")

        if not exp:
            return True

        return time.time() >= exp - 300

    except Exception:
        return True


def get_token_expiry():
    """Returns access token expiry timestamp."""
    token = get_access_token()

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        return payload.get("exp")

    except Exception:
        return None


def ensure_valid_token() -> str:
    """
    Ensure a valid FYERS access token is available.

    Returns the access token. Renews via browser login when expired or missing.
    """
    if TOKEN_FILE.exists() and not token_expired():
        token = get_access_token()
        if token:
            return token

    log_info("Token missing or expired — starting automatic renewal")
    return _renew_token()


def _renew_token() -> str:
    config_errors = validate_auth_config()
    if config_errors:
        raise TokenRenewalError(
            "Configuration error: " + "; ".join(config_errors)
        )

    try:
        login_url = get_login_url()
    except Exception as exc:
        raise TokenRenewalError(
            f"Failed to generate FYERS login URL: {exc}"
        ) from exc

    try:
        auth_code = run_browser_login(login_url)
    except BrowserLoginError as exc:
        raise TokenRenewalError(f"Browser login failed: {exc}") from exc

    log_info("Auth code captured — exchanging for access token")

    try:
        token_response = generate_access_token(auth_code)
    except Exception as exc:
        raise TokenRenewalError(
            f"Failed to exchange auth_code for token: {exc}"
        ) from exc

    if not isinstance(token_response, dict):
        raise TokenRenewalError(
            f"Unexpected token response type: {type(token_response)}"
        )

    status = str(token_response.get("s", "")).lower()
    if status == "error":
        message = token_response.get("message", "Unknown FYERS API error")
        raise TokenRenewalError(f"Token exchange failed: {message}")

    access_token = token_response.get("access_token")
    if not access_token:
        raise TokenRenewalError(
            "Token exchange response did not include access_token"
        )

    save_tokens(token_response)
    log_info("Token generated and saved to fyers_token.json")

    _verify_token()
    return access_token


def _verify_token() -> None:
    """Verify the saved token by calling FYERS get_profile()."""
    try:
        fyers = fyersModel.FyersModel(
            client_id=CLIENT_ID,
            token=get_access_token(),
            is_async=False,
        )
        profile = fyers.get_profile()
    except Exception as exc:
        raise TokenRenewalError(
            f"Token verification failed (get_profile error): {exc}"
        ) from exc

    if not isinstance(profile, dict):
        raise TokenRenewalError(
            f"Unexpected get_profile() response: {profile}"
        )

    status = profile.get("s", "").lower()
    if status == "ok":
        log_info("Verification successful")
        name = (
            profile.get("data", {}).get("name")
            or profile.get("data", {}).get("fy_id")
            or "FYERS user"
        )
        print(f"FYERS authentication successful: {name}")
        return

    code = profile.get("code")
    message = profile.get("message", "Unknown error")
    raise TokenRenewalError(
        f"Token verification failed (code={code}): {message}"
    )


def refresh_access_token():
    """Renew access token via browser login."""
    log_warning("Refreshing access token via browser login")
    return _renew_token()


def get_valid_access_token():
    """Returns a valid access token, renewing automatically if needed."""
    return ensure_valid_token()
