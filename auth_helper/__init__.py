"""
FYERS automatic login and token renewal utility.

Public API for the trading engine:
    from auth_helper import ensure_valid_token
"""

from auth_helper.token_manager import ensure_valid_token

__all__ = ["ensure_valid_token"]
