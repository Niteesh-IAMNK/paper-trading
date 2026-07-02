import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
)
from .logger import (
    log_info,
    log_error,
)

IST = ZoneInfo(TIMEZONE)


def send_message(message: str):
    """
    Send a Telegram message.
    """
    if not TELEGRAM_BOT_TOKEN:
        log_info(f"[TELEGRAM DISABLED]\n{message}")
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        f"/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return True

    except Exception as e:
        log_error(f"Telegram Error: {e}")
        return False


def _format_symbol(symbol: str) -> str:
    if not symbol:
        return ""

    cleaned = symbol.replace("NSE:", "")
    if cleaned.endswith("CE"):
        body = cleaned[:-2]
        return f"{body} CE"
    if cleaned.endswith("PE"):
        body = cleaned[:-2]
        return f"{body} PE"
    return cleaned


def _format_time(timestamp: datetime | None = None) -> str:
    current = timestamp or datetime.now(IST)
    return current.strftime("%H:%M")


def send_trade_buy(
    ai_name: str,
    symbol: str,
    price: float,
    quantity: int,
    timestamp: datetime | None = None,
):
    message = (
        f"{ai_name.upper()}\n"
        f"BUY\n"
        f"{_format_symbol(symbol)}\n"
        f"Price: {price:.2f}\n"
        f"Qty: {quantity}\n"
        f"Time: {_format_time(timestamp)}"
    )
    return send_message(message)


def send_trade_sell(
    ai_name: str,
    symbol: str,
    exit_price: float,
    pnl: float,
    reason: str = "",
    timestamp: datetime | None = None,
):
    pnl_text = f"{pnl:+.2f}"
    message = (
        f"{ai_name.upper()}\n"
        f"SELL\n"
        f"{_format_symbol(symbol)}\n"
        f"Exit: {exit_price:.2f}\n"
        f"PnL: {pnl_text}\n"
        f"Reason:\n{reason}"
    )
    return send_message(message)


def send_ai_engine_error(ai_name: str, error_message: str):
    message = (
        f"⚠️ {ai_name.upper()} Engine Error\n\n"
        f"{error_message}"
    )
    return send_message(message)


def send_trade_message(
    ai_name,
    action,
    symbol,
    quantity,
    price,
    reason="",
):
    if action == "BUY":
        return send_trade_buy(
            ai_name,
            symbol,
            price,
            quantity,
        )

    return send_trade_sell(
        ai_name,
        symbol,
        price,
        0.0,
        reason,
    )


def send_daily_summary_message(summary: str):
    return send_message(summary)
