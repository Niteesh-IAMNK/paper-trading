"""
Local HTTP callback server for capturing FYERS auth_code.

Only started when FYERS_REDIRECT_URI points to a local HTTP endpoint.
Browser URL monitoring is used as a fallback for other redirect URIs.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from auth_helper.config import parse_redirect_uri
from auth_helper.logger import log_error, log_info


class AuthCodeCapture:
    """Thread-safe holder for a captured auth_code."""

    def __init__(self) -> None:
        self._auth_code: str | None = None
        self._event = threading.Event()
        self._lock = threading.Lock()

    @property
    def auth_code(self) -> str | None:
        with self._lock:
            return self._auth_code

    def set_auth_code(self, code: str) -> None:
        with self._lock:
            if self._auth_code is None:
                self._auth_code = code
                self._event.set()

    def wait(self, timeout: float | None = None) -> str | None:
        self._event.wait(timeout=timeout)
        return self.auth_code


def extract_auth_code_from_url(url: str) -> str | None:
    """Extract auth_code from a redirect URL query string."""
    if not url or "auth_code=" not in url:
        return None

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    codes = params.get("auth_code") or params.get("code")
    if codes:
        return codes[0]

    # Fallback: manual parse for malformed URLs
    try:
        start = url.index("auth_code=") + len("auth_code=")
        remainder = url[start:]
        end = remainder.find("&")
        return remainder[:end] if end != -1 else remainder
    except ValueError:
        return None


class CallbackServer:
    """Runs a minimal HTTP server to receive the OAuth redirect."""

    def __init__(self, capture: AuthCodeCapture) -> None:
        self.capture = capture
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        host, port, path, use_local = parse_redirect_uri()
        self.host = host
        self.port = port
        self.path = path.rstrip("/") or "/"
        self.use_local_server = use_local

    def start(self) -> bool:
        if not self.use_local_server:
            log_info(
                "Redirect URI is not a local HTTP endpoint; "
                "using browser URL monitoring only."
            )
            return False

        handler_factory = _make_handler(self.path, self.capture)
        self._server = HTTPServer((self.host, self.port), handler_factory)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="fyers-callback-server",
            daemon=True,
        )
        self._thread.start()
        log_info(
            f"Callback server listening on http://{self.host}:{self.port}{self.path}"
        )
        return True

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None


def _make_handler(
    expected_path: str,
    capture: AuthCodeCapture,
) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def log_message(
            self,
            fmt: str,
            *args: object,
        ) -> None:
            # Suppress default stderr logging; we log explicitly.
            pass

        def do_GET(self) -> None:
            request_path = urlparse(self.path).path.rstrip("/") or "/"
            auth_code = extract_auth_code_from_url(self.path)

            if auth_code:
                capture.set_auth_code(auth_code)
                log_info("Auth code captured via callback server")
                body = (
                    "<html><body><h2>FYERS login successful.</h2>"
                    "<p>You may close this window.</p></body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                return

            if request_path != expected_path:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><p>Waiting for FYERS redirect...</p></body></html>"
            )

        def do_POST(self) -> None:
            self.do_GET()

    return _Handler


def monitor_page_for_auth_code(
    get_url: Callable[[], str],
    capture: AuthCodeCapture,
    timeout_ms: int,
    poll_interval_ms: int = 2000,
) -> str | None:
    """
    Poll the browser URL until auth_code appears or timeout is reached.
    """
    import time

    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if capture.auth_code:
            return capture.auth_code

        url = get_url()
        auth_code = extract_auth_code_from_url(url)
        if auth_code:
            capture.set_auth_code(auth_code)
            log_info("Auth code captured from browser redirect URL")
            return auth_code

        time.sleep(poll_interval_ms / 1000)

    log_error("Timed out waiting for auth_code redirect")
    return None
