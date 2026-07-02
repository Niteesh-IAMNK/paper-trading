"""
Microsoft Edge browser automation for FYERS login via Playwright.

Uses a dedicated persistent profile so other Edge profiles are not affected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from auth_helper.callback_server import (
    AuthCodeCapture,
    CallbackServer,
    monitor_page_for_auth_code,
)
from auth_helper.config import (
    BROWSER_CHANNEL,
    BROWSER_PROFILE_DIR,
    FYERS_PIN,
    FYERS_USER_ID,
    HEADLESS,
    LOGIN_TIMEOUT_MS,
    OTP_POLL_INTERVAL_MS,
    validate_config,
)
from auth_helper.logger import log_error, log_exception, log_info, log_warning

if TYPE_CHECKING:
    from playwright.sync_api import Page, Playwright


class BrowserLoginError(Exception):
    """Raised when automated browser login fails."""


def run_browser_login(login_url: str) -> str:
    """
    Launch Edge, complete FYERS login, and return the auth_code.

    User ID and PIN are filled automatically. If OTP is required, the flow
    pauses until the user completes it manually in the browser.
    """
    config_errors = validate_config()
    if config_errors:
        raise BrowserLoginError(
            "Invalid configuration: " + "; ".join(config_errors)
        )

    log_info("Login started")
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    capture = AuthCodeCapture()
    callback = CallbackServer(capture)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserLoginError(
            "Playwright is not installed. "
            "Run: pip install -r auth_helper/requirements.txt "
            "&& playwright install msedge"
        ) from exc

    callback.start()

    try:
        with sync_playwright() as playwright:
            log_info("Browser launched (Microsoft Edge)")
            context = _launch_edge_context(playwright)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
                _perform_login(page)
                auth_code = _wait_for_auth_code(page, capture, callback)
                if not auth_code:
                    raise BrowserLoginError(
                        "Failed to capture auth_code from redirect"
                    )
                return auth_code
            finally:
                context.close()
    except BrowserLoginError:
        raise
    except Exception as exc:
        log_exception(f"Browser login failed: {exc}")
        raise BrowserLoginError(str(exc)) from exc
    finally:
        callback.stop()


def _launch_edge_context(playwright: Playwright):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE_DIR),
        channel=BROWSER_CHANNEL,
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
        ],
        viewport={"width": 1280, "height": 900},
        ignore_https_errors=True,
    )


def _perform_login(page: Page) -> None:
    """Enter User ID and PIN on the FYERS login page."""
    _click_login_with_client_id(page)
    _fill_user_id(page)
    _fill_pin(page)
    _submit_pin(page)
    _handle_otp_if_required(page)


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


def _fill_user_id(page: Page) -> None:
    selectors = ["#fy_client_id", "input[name='fy_id']", "#clientId"]
    filled = False
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.fill(FYERS_USER_ID)
            locator.first.press("Enter")
            filled = True
            log_info("User ID entered")
            page.wait_for_timeout(1500)
            break

    if not filled:
        raise BrowserLoginError(
            "Could not find FYERS User ID input field on login page"
        )


def _fill_pin(page: Page) -> None:
    pin = FYERS_PIN
    if len(pin) != 4:
        raise BrowserLoginError("FYERS_PIN must be exactly 4 digits")

    # FYERS uses four separate digit inputs inside verifyPinForm
    pin_form = page.locator("#verifyPinForm")
    if pin_form.count() > 0:
        digits = ["#first", "#second", "#third", "#fourth"]
        for index, digit_selector in enumerate(digits):
            field = pin_form.locator(digit_selector)
            if field.count() > 0:
                field.fill(pin[index])
        log_info("PIN entered")
        return

    # Fallback: single PIN input
    single_pin = page.locator(
        "input[type='password'], input[placeholder*='PIN'], input[name='pin']"
    )
    if single_pin.count() > 0:
        single_pin.first.fill(pin)
        log_info("PIN entered")
        return

    raise BrowserLoginError("Could not find PIN input fields on login page")


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
    """Pause for manual OTP entry when the OTP/TOTP screen is shown."""
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
                    log_info(
                        "OTP required — waiting for user to complete it manually"
                    )
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
    """Wait for redirect containing auth_code."""
    # App permission screen may appear after PIN/OTP
    _click_allow_if_present(page)

    return monitor_page_for_auth_code(
        get_url=lambda: page.url,
        capture=capture,
        timeout_ms=LOGIN_TIMEOUT_MS,
        poll_interval_ms=OTP_POLL_INTERVAL_MS,
    )


def _click_allow_if_present(page: Page) -> None:
    """Click through FYERS app permission / consent screens if shown."""
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
