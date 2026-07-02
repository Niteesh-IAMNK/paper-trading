"""Unit tests for FYERS authentication logic (no live API required)."""

from unittest.mock import patch

from shared.fyers_callback import extract_auth_code_from_url
from shared.fyers_token_manager import (
    TokenRenewalError,
    _is_auth_failure,
    _renew_token_with_retries,
    token_expired,
)


def test_extract_auth_code_from_url():
    url = "https://127.0.0.1:5000/?auth_code=ABC123&state=xyz"
    assert extract_auth_code_from_url(url) == "ABC123"


def test_is_auth_failure_detects_invalid_token():
    profile = {
        "s": "error",
        "code": -17,
        "message": "Could not authenticate the user",
    }
    assert _is_auth_failure(profile) is True


def test_is_auth_failure_accepts_ok_profile():
    profile = {"s": "ok", "code": 200, "data": {"name": "Test User"}}
    assert _is_auth_failure(profile) is False


def test_token_expired_without_token_file():
    with patch(
        "shared.fyers_token_manager.get_access_token",
        return_value=None,
    ):
        assert token_expired() is True


def test_renew_token_with_retries_fails_fast_on_config_error():
    with patch(
        "shared.fyers_token_manager.validate_auth_config",
        return_value=["FYERS_PIN is not set"],
    ):
        try:
            _renew_token_with_retries()
            raised = False
        except TokenRenewalError as exc:
            raised = True
            assert "Configuration error" in str(exc)

        assert raised


def test_renew_token_with_retries_attempts_three_times():
    with patch(
        "shared.fyers_token_manager.validate_auth_config",
        return_value=[],
    ), patch(
        "shared.fyers_token_manager._renew_token",
        side_effect=TokenRenewalError("browser failed"),
    ) as renew_mock:
        try:
            _renew_token_with_retries()
            raised = False
        except TokenRenewalError as exc:
            raised = True
            assert "3 attempts" in str(exc)

        assert raised
        assert renew_mock.call_count == 3


if __name__ == "__main__":
    tests = [
        test_extract_auth_code_from_url,
        test_is_auth_failure_detects_invalid_token,
        test_is_auth_failure_accepts_ok_profile,
        test_token_expired_without_token_file,
        test_renew_token_with_retries_fails_fast_on_config_error,
        test_renew_token_with_retries_attempts_three_times,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print("All auth unit tests passed.")
