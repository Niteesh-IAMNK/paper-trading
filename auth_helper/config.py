"""
Configuration for the FYERS auth utility.

Credentials are loaded from environment variables (typically via .env).
PIN defaults are defined here — override with FYERS_PIN in production.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

# Project root (parent of auth_helper/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# FYERS API credentials (shared with trading engine via .env)
FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID", "")
FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "")
FYERS_REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI", "")

# FYERS account credentials for browser login
FYERS_USER_ID = os.getenv("FYERS_USER_ID", "")

# 4-digit trading PIN — configurable, not hardcoded in browser logic
DEFAULT_PIN = "2009"
FYERS_PIN = os.getenv("FYERS_PIN", DEFAULT_PIN)

# Paths
TOKEN_FILE = PROJECT_ROOT / "fyers_token.json"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "auth.log"
BROWSER_PROFILE_DIR = PROJECT_ROOT / "profiles" / "fyers"

# Browser behaviour
BROWSER_CHANNEL = "msedge"
HEADLESS = os.getenv("FYERS_AUTH_HEADLESS", "false").lower() == "true"
LOGIN_TIMEOUT_MS = int(os.getenv("FYERS_AUTH_TIMEOUT_MS", "300000"))  # 5 minutes
OTP_POLL_INTERVAL_MS = 2000


def validate_config() -> list[str]:
    """Return a list of missing or invalid configuration values."""
    errors: list[str] = []

    if not FYERS_CLIENT_ID:
        errors.append("FYERS_CLIENT_ID is not set")
    if not FYERS_SECRET_KEY:
        errors.append("FYERS_SECRET_KEY is not set")
    if not FYERS_REDIRECT_URI:
        errors.append("FYERS_REDIRECT_URI is not set")
    if not FYERS_USER_ID:
        errors.append("FYERS_USER_ID is not set")
    if not FYERS_PIN or len(FYERS_PIN) != 4 or not FYERS_PIN.isdigit():
        errors.append("FYERS_PIN must be a 4-digit numeric PIN")

    return errors


def parse_redirect_uri() -> tuple[str, int, str, bool]:
    """
    Parse FYERS_REDIRECT_URI into host, port, path, and whether a local
    callback server can be started.
    """
    parsed = urlparse(FYERS_REDIRECT_URI)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    use_local_server = (
        parsed.scheme == "http"
        and host in {"127.0.0.1", "localhost"}
    )
    return host, port, path, use_local_server
