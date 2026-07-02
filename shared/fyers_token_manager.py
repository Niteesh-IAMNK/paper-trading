import json
import os
import sys
import threading
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
from shared.telegram_bot import send_message

TOKEN_FILE = Path("fyers_token.json")
LOCK_FILE = Path("profiles/fyers/.auth.lock")
MAX_RENEWAL_ATTEMPTS = 3
LOCK_TIMEOUT_SECONDS = 600

_THREAD_LOCK = threading.Lock()
_session_validated = False
_renewal_performed = False

TELEGRAM_SUCCESS = (
    "✅ FYERS Login Successful\n\n"
    "Access token renewed.\n\n"
    "Trading engine starting..."
)
TELEGRAM_FAILURE = (
    "❌ FYERS Login Failed\n\n"
    "Trading engine NOT started.\n\n"
    "Manual intervention required."
)


class TokenRenewalError(Exception):
    """Raised when token renewal or verification fails."""


class AuthLockTimeout(TokenRenewalError):
    """Raised when waiting for the authentication lock times out."""


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


def _build_fyers_client(access_token: str | None = None):
    return fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=access_token or get_access_token(),
        is_async=False,
    )


def _is_auth_failure(profile: object) -> bool:
    """Return True when get_profile() indicates an authentication problem."""
    if not isinstance(profile, dict):
        return True

    status = str(profile.get("s", "")).lower()
    if status == "ok":
        return False

    code = profile.get("code")
    message = str(profile.get("message", "")).lower()

    auth_codes = {-17, 403, 401, -16, -18}
    if code in auth_codes:
        return True

    auth_keywords = (
        "auth",
        "token",
        "expired",
        "invalid",
        "permission",
        "login",
    )
    return any(keyword in message for keyword in auth_keywords)


def _verify_profile_for_token(access_token: str | None = None) -> dict:
    """
    Call get_profile() and return the profile on success.

    Raises TokenRenewalError when the token is rejected.
    """
    log_info("Verifying account with get_profile()...")

    try:
        profile = _build_fyers_client(access_token).get_profile()
    except Exception as exc:
        raise TokenRenewalError(
            f"Verifying account failed (get_profile request error): {exc}"
        ) from exc

    if _is_auth_failure(profile):
        code = profile.get("code") if isinstance(profile, dict) else None
        message = (
            profile.get("message", "Unknown error")
            if isinstance(profile, dict)
            else str(profile)
        )
        raise TokenRenewalError(
            f"Verifying account failed (get_profile auth error, code={code}): "
            f"{message}"
        )

    return profile


def _acquire_auth_lock():
    """Acquire in-process and cross-process authentication locks."""
    _THREAD_LOCK.acquire()
    lock_handle = None
    deadline = time.time() + LOCK_TIMEOUT_SECONDS

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    while time.time() < deadline:
        try:
            lock_handle = open(LOCK_FILE, "a+")
            if sys.platform == "win32":
                import msvcrt

                lock_handle.seek(0)
                msvcrt.locking(
                    lock_handle.fileno(),
                    msvcrt.LK_NBLCK,
                    1,
                )
            else:
                import fcntl

                fcntl.flock(
                    lock_handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )

            lock_handle.seek(0)
            lock_handle.truncate()
            lock_handle.write(str(os.getpid()))
            lock_handle.flush()
            return lock_handle

        except (OSError, BlockingIOError):
            if lock_handle is not None:
                lock_handle.close()
                lock_handle = None
            log_info(
                "Authentication already in progress — waiting for lock..."
            )
            time.sleep(2)

    _THREAD_LOCK.release()
    raise AuthLockTimeout(
        "Timed out waiting for another authentication process to finish"
    )


def _release_auth_lock(lock_handle) -> None:
    if lock_handle is not None:
        try:
            if sys.platform == "win32":
                import msvcrt

                lock_handle.seek(0)
                msvcrt.locking(
                    lock_handle.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                import fcntl

                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()

    if _THREAD_LOCK.locked():
        _THREAD_LOCK.release()


class auth_lock:
    """Context manager for authentication locking."""

    def __enter__(self):
        self._handle = _acquire_auth_lock()
        return self

    def __exit__(self, exc_type, exc, tb):
        _release_auth_lock(self._handle)
        return False


def ensure_valid_token() -> str:
    """
    Ensure a valid FYERS access token is available.

    Uses JWT expiry as a fast pre-check, then validates with get_profile().
    Renews automatically when verification fails.
    """
    global _session_validated

    if _session_validated:
        token = get_access_token()
        if token:
            return token

    with auth_lock():
        token = _resolve_valid_token(notify_on_renewal=False)
        _session_validated = True
        return token


def bootstrap_authentication() -> None:
    """
    Startup authentication gate.

    Verifies or renews the token before the trading engine starts.
    Exits the process gracefully when renewal fails after all retries.
    """
    global _session_validated, _renewal_performed

    log_info("Checking token...")

    try:
        with auth_lock():
            token = _resolve_valid_token(notify_on_renewal=True)
            _session_validated = True
            log_info("Authentication successful")
            print(f"FYERS token ready ({token[:12]}...)")
    except TokenRenewalError as exc:
        log_error(f"Authentication failed: {exc}")
        send_message(TELEGRAM_FAILURE)
        print(
            "\n❌ FYERS Login Failed\n"
            "Trading engine NOT started.\n"
            "Manual intervention required.\n"
            f"Details: {exc}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _resolve_valid_token(notify_on_renewal: bool) -> str:
    global _renewal_performed

    token = get_access_token()

    if not token:
        log_info("No token found in fyers_token.json")
    elif token_expired():
        log_info("Token expired")
    else:
        log_info("JWT still valid — verifying with API")
        try:
            _verify_profile_for_token(token)
            log_info("Existing token accepted by get_profile()")
            return token
        except TokenRenewalError as exc:
            log_warning(
                "Stored token rejected by get_profile() — renewal required: "
                f"{exc}"
            )

    token = _renew_token_with_retries()
    _renewal_performed = True

    if notify_on_renewal:
        send_message(TELEGRAM_SUCCESS)

    return token


def _renew_token_with_retries() -> str:
    config_errors = validate_auth_config()
    if config_errors:
        raise TokenRenewalError(
            "Configuration error: " + "; ".join(config_errors)
        )

    last_error: TokenRenewalError | None = None

    for attempt in range(1, MAX_RENEWAL_ATTEMPTS + 1):
        log_info(f"Renewal attempt {attempt}/{MAX_RENEWAL_ATTEMPTS}")
        try:
            return _renew_token()
        except TokenRenewalError as exc:
            last_error = exc
            log_error(f"Renewal attempt {attempt} failed: {exc}")

    message = (
        f"Token renewal failed after {MAX_RENEWAL_ATTEMPTS} attempts"
    )
    if last_error is not None:
        message = f"{message}: {last_error}"

    raise TokenRenewalError(message)


def _renew_token() -> str:
    try:
        login_url = get_login_url()
    except Exception as exc:
        raise TokenRenewalError(
            f"Failed to generate FYERS login URL: {exc}"
        ) from exc

    try:
        auth_code = run_browser_login(login_url)
    except BrowserLoginError as exc:
        raise TokenRenewalError(
            f"Browser login step failed: {exc}"
        ) from exc

    log_info("Redirect received — generating access token")

    try:
        token_response = generate_access_token(auth_code)
    except Exception as exc:
        raise TokenRenewalError(
            f"Generating access token failed: {exc}"
        ) from exc

    if not isinstance(token_response, dict):
        raise TokenRenewalError(
            f"Unexpected token response type: {type(token_response)}"
        )

    status = str(token_response.get("s", "")).lower()
    if status == "error":
        message = token_response.get("message", "Unknown FYERS API error")
        raise TokenRenewalError(
            f"Generating access token failed (API error): {message}"
        )

    access_token = token_response.get("access_token")
    if not access_token:
        raise TokenRenewalError(
            "Generating access token failed: access_token missing in response"
        )

    log_info("Saving fyers_token.json...")
    save_tokens(token_response)
    log_info("fyers_token.json saved")

    profile = _verify_profile_for_token(access_token)
    name = (
        profile.get("data", {}).get("name")
        or profile.get("data", {}).get("fy_id")
        or "FYERS user"
    )
    log_info(f"Authentication successful for {name}")
    print(f"FYERS authentication successful: {name}")

    return access_token


def refresh_access_token():
    """Renew access token via browser login."""
    log_warning("Refreshing access token via browser login")
    return _renew_token_with_retries()


def get_valid_access_token():
    """Returns a valid access token, renewing automatically if needed."""
    return ensure_valid_token()
