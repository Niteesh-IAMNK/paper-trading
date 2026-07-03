"""
Microsoft Edge browser automation for FYERS login via Playwright.

Uses a dedicated persistent profile at profiles/fyers/.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from shared.fyers_auth import (
    FYERS_PIN,
    FYERS_USER_ID,
    validate_auth_config,
)
from shared.fyers_callback import (
    AuthCodeCapture,
    CallbackServer,
    extract_auth_code_from_url,
)
from shared.fyers_logger import log_error, log_exception, log_info, log_warning

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page, Playwright

BROWSER_PROFILE_DIR = Path("profiles/fyers")
BROWSER_CHANNEL = "msedge"
HEADLESS = os.getenv("FYERS_AUTH_HEADLESS", "false").lower() == "true"
LOGIN_TIMEOUT_MS = int(os.getenv("FYERS_AUTH_TIMEOUT_MS", "300000"))
OTP_POLL_INTERVAL_MS = 2000


class BrowserLoginError(Exception):
    """Raised when automated browser login fails."""


def run_browser_login(login_url: str) -> str:
    """
    Launch Edge, complete FYERS login, and return the auth_code.

    User ID and PIN are filled automatically when visible. If OTP, an
    unexpected screen, or missing fields require user action, the browser
    stays open until the redirect auth_code is captured or the timeout
    expires (default 5 minutes).
    """
    config_errors = validate_auth_config()
    if config_errors:
        raise BrowserLoginError(
            "Invalid configuration: " + "; ".join(config_errors)
        )

    log_info("Waiting for login...")
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    capture = AuthCodeCapture()
    callback = CallbackServer(capture)
    playwright: Playwright | None = None
    context: BrowserContext | None = None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserLoginError(
            "Playwright is not installed. "
            "Run: pip install -r requirements.txt && playwright install msedge"
        ) from exc

    try:
        callback.start()
        log_info("Launching Microsoft Edge...")
        playwright = sync_playwright().start()
        context = _launch_edge_context(playwright)

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        _perform_login(page)

        auth_code = _wait_for_auth_code(page, capture, callback)
        if not auth_code:
            raise BrowserLoginError(
                "Redirect step failed: auth_code not captured from redirect URL"
            )

        log_info("Redirect received")
        return auth_code

    except BrowserLoginError:
        raise
    except Exception as exc:
        log_exception(f"Browser login step failed: {exc}")
        raise BrowserLoginError(str(exc)) from exc
    finally:
        if context is not None:
            try:
                context.close()
                log_info("Edge browser closed")
            except Exception as exc:
                log_warning(f"Closing Edge browser failed: {exc}")

        if playwright is not None:
            try:
                playwright.stop()
                log_info("Playwright stopped")
            except Exception as exc:
                log_warning(f"Stopping Playwright failed: {exc}")

        try:
            callback.stop()
            log_info("Callback server stopped")
        except Exception as exc:
            log_warning(f"Stopping callback server failed: {exc}")


def _launch_edge_context(playwright: Playwright):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE_DIR),
        channel=BROWSER_CHANNEL,
        headless=HEADLESS,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
    )


def _perform_login(page: Page) -> None:
    """
    Attempt automatic User ID / PIN entry when fields are visible.

    Never raises when fields are missing — the caller waits for manual
    completion and watches for the redirect auth_code instead.
    """
    page.wait_for_timeout(1000)
    _click_login_with_client_id(page)

    user_id_filled = _try_fill_user_id(page)
    pin_filled = False

    if user_id_filled or _pin_fields_visible(page):
        pin_filled = _try_fill_pin(page)
        if pin_filled:
            _submit_pin(page)

    _handle_otp_if_required(page)

    if not user_id_filled:
        _log_manual_login_required()


def _log_manual_login_required() -> None:
    minutes = max(1, LOGIN_TIMEOUT_MS // 60000)
    message = (
        "Manual login required. Waiting for user completion..."
    )
    log_info(message)
    print(
        "\n>>> Manual login required. Complete login in the Edge window "
        "(User ID, PIN, OTP, or any security checks). "
        f"Waiting up to {minutes} minutes for redirect...\n"
    )


def _pin_fields_visible(page: Page) -> bool:
    try:
        if page.locator("#verifyPinForm").count() > 0:
            return True

        single_pin = page.locator(
            "input[type='password'], input[placeholder*='PIN'], input[name='pin']"
        )
        return single_pin.count() > 0 and single_pin.first.is_visible(timeout=1000)
    except Exception:
        return False


def _try_fill_user_id(page: Page) -> bool:
    selectors = ["#fy_client_id", "input[name='fy_id']", "#clientId"]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            try:
                if locator.first.is_visible(timeout=3000):
                    locator.first.fill(FYERS_USER_ID)
                    locator.first.press("Enter")
                    log_info("User ID entered")
                    page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue

    log_warning("FYERS User ID input field not found")
    return False


def _try_fill_pin(page: Page) -> bool:
    pin = FYERS_PIN
    if len(pin) != 4:
        log_warning("FYERS_PIN must be exactly 4 digits; skipping PIN autofill")
        return False

    pin_form = page.locator("#verifyPinForm")
    if pin_form.count() > 0:
        try:
            digits = ["#first", "#second", "#third", "#fourth"]
            for index, digit_selector in enumerate(digits):
                field = pin_form.locator(digit_selector)
                if field.count() > 0:
                    field.fill(pin[index])
            log_info("PIN entered")
            return True
        except Exception as exc:
            log_warning(f"PIN autofill failed: {exc}")
            return False

    single_pin = page.locator(
        "input[type='password'], input[placeholder*='PIN'], input[name='pin']"
    )
    if single_pin.count() > 0:
        try:
            if single_pin.first.is_visible(timeout=3000):
                single_pin.first.fill(pin)
                log_info("PIN entered")
                return True
        except Exception as exc:
            log_warning(f"PIN autofill failed: {exc}")
            return False

    log_warning("PIN input fields not found")
    return False


def _click_login_with_client_id(page: Page) -> None:
    selectors = [
        "#login_client_id",
        "text=Login with client ID",
        "text=Login with Client ID",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            try:
                locator.first.click(timeout=5000)
                page.wait_for_timeout(1000)
                return
            except Exception:
                continue


def _submit_pin(page: Page) -> None:
    selectors = ["#verifyPinSubmit", "button:has-text('Submit')", "text=Submit"]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            try:
                locator.first.click(timeout=5000)
                page.wait_for_timeout(2000)
                return
            except Exception:
                continue
    log_warning("PIN submit button not found; login may continue automatically")


def _handle_otp_if_required(page: Page) -> None:
    otp_indicators = [
        "#confirmOtpSubmit",
        "text=Enter the 6-digit OTP",
        "text=Enter a 6 digit TOTP",
        "text=6-digit OTP",
    ]

    for selector in otp_indicators:
        locator = page.locator(selector)
        if locator.count() > 0:
            try:
                if locator.first.is_visible(timeout=3000):
                    log_info("Waiting for OTP...")
                    print(
                        "\n>>> OTP required. Complete OTP in the Edge window. "
                        "Waiting for redirect...\n"
                    )
                    return
            except Exception:
                continue


def _wait_for_auth_code(
    page: Page,
    capture: AuthCodeCapture,
    callback: CallbackServer,
) -> str | None:
    """
    Poll the browser and callback server until auth_code appears.

    Keeps Edge open for manual OTP / security screens while retrying
    opportunistic autofill and authorize clicks on each poll.
    """
    _click_allow_if_present(page)

    deadline = time.time() + (LOGIN_TIMEOUT_MS / 1000)
    poll_seconds = OTP_POLL_INTERVAL_MS / 1000

    while time.time() < deadline:
        if capture.auth_code:
            return capture.auth_code

        auth_code = extract_auth_code_from_url(page.url)
        if auth_code:
            capture.set_auth_code(auth_code)
            log_info("Auth code captured from browser redirect URL")
            return auth_code

        _click_allow_if_present(page)
        _handle_otp_if_required(page)

        if _try_fill_user_id(page) and _try_fill_pin(page):
            _submit_pin(page)

        time.sleep(poll_seconds)

    log_error(
        f"Timed out waiting for auth_code redirect after "
        f"{LOGIN_TIMEOUT_MS // 60000} minutes"
    )
    return None


def _click_allow_if_present(page: Page) -> None:
    allow_selectors = [
        "text=Allow",
        "text=Authorize",
        "text=Grant",
        "button:has-text('Allow')",
        "button:has-text('Authorize')",
    ]
    for selector in allow_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            try:
                if locator.first.is_visible(timeout=2000):
                    locator.first.click(timeout=3000)
                    page.wait_for_timeout(1500)
                    return
            except Exception:
                continue
