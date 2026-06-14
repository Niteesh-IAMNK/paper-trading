import requests

from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)
from .logger import (
    log_info,
    log_error
)


def send_message(
    message: str
):
    """
    Send a Telegram message.
    """

    if not TELEGRAM_BOT_TOKEN:
        log_info(
            f"[TELEGRAM DISABLED]\n{message}"
        )
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        f"/sendMessage"
    )

    payload = {
        "chat_id":
            TELEGRAM_CHAT_ID,
        "text":
            message
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        response.raise_for_status()

        return True

    except Exception as e:
        log_error(
            f"Telegram Error: {e}"
        )

        return False


def send_trade_message(
    ai_name,
    action,
    symbol,
    quantity,
    price,
    reason=""
):
    message = (
        f"🤖 {ai_name}\n"
        f"{action}\n"
        f"{symbol}\n"
        f"Qty: {quantity}\n"
        f"Price: ₹{price}\n"
    )

    if reason:
        message += (
            f"Reason:\n{reason}"
        )

    return send_message(
        message
    )


def send_daily_summary(
    summary: str
):
    return send_message(
        summary
    )