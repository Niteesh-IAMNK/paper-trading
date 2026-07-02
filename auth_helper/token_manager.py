"""
Token lifecycle management for FYERS authentication.

Reuses shared token helpers and orchestrates browser login when renewal
is required.
"""

from __future__ import annotations

import sys

from fyers_apiv3 import fyersModel

from auth_helper.browser import BrowserLoginError, run_browser_login
from auth_helper.config import FYERS_CLIENT_ID, TOKEN_FILE, validate_config
from auth_helper.logger import log_error, log_info, log_warning
from shared.fyers_auth import generate_access_token, get_login_url
from shared.fyers_token_manager import (
    get_access_token,
    save_tokens,
    token_expired,
)


class TokenRenewalError(Exception):
    """Raised when token renewal or verification fails."""


def ensure_valid_token() -> str:
    """
    Ensure a valid FYERS access token is available.

    Returns the access token string. Renews via browser login when expired
    or missing. Safe to call from the trading engine before API requests.
    """
    if TOKEN_FILE.exists() and not token_expired():
        token = get_access_token()
        if token:
            return token

    log_info("Token missing or expired — starting renewal")
    return _renew_token()


def _renew_token() -> str:
    config_errors = validate_config()
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

    if token_response.get("s") == "error" or token_response.get("s") == "ERROR":
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
    # Build client directly to avoid recursion through get_fyers().
    try:
        fyers = fyersModel.FyersModel(
            client_id=FYERS_CLIENT_ID,
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
        print(f"Success: authenticated as {name}")
        return

    code = profile.get("code")
    message = profile.get("message", "Unknown error")
    raise TokenRenewalError(
        f"Token verification failed (code={code}): {message}"
    )


def run_standalone() -> int:
    """
    CLI entry behaviour: exit immediately when token is already valid.
    Returns process exit code.
    """
    log_info("FYERS auth utility started")

    if TOKEN_FILE.exists() and not token_expired():
        log_info("Token is still valid — exiting")
        print("Token is valid. No renewal needed.")
        return 0

    if not TOKEN_FILE.exists():
        log_warning("fyers_token.json not found — renewal required")
    else:
        log_warning("Token expired — renewal required")

    try:
        ensure_valid_token()
    except TokenRenewalError as exc:
        log_error(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("FYERS token renewal completed successfully.")
    return 0
