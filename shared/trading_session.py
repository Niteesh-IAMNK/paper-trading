from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo(
    "Asia/Kolkata"
)


def current_time():

    return (
        datetime.now(
            IST
        ).strftime(
            "%H:%M"
        )
    )


def is_market_open():

    now = current_time()

    return (
        "09:15" <= now < "15:30"
    )


def is_analysis_time():

    now = current_time()

    return (
        "09:15" <= now < "10:30"
    )


def is_trading_time():

    now = current_time()

    return (
        "10:30" <= now < "15:20"
    )


def is_square_off_time():

    now = current_time()

    return (
        "15:20" <= now < "15:30"
    )