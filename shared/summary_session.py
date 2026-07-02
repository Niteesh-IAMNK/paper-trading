from datetime import (
    datetime
)
from zoneinfo import (
    ZoneInfo
)

from shared.config import MARKET_CLOSE

IST = ZoneInfo(
    "Asia/Kolkata"
)

_SUMMARY_TIME = MARKET_CLOSE[:5]


def is_summary_time():

    now = datetime.now(
        IST
    ).strftime(
        "%H:%M"
    )

    return (
        _SUMMARY_TIME
        <= now <
        "15:31"
    )