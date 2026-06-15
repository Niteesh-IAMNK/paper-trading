from datetime import (
    datetime
)
from zoneinfo import (
    ZoneInfo
)

IST = ZoneInfo(
    "Asia/Kolkata"
)


def is_summary_time():

    now = datetime.now(
        IST
    ).strftime(
        "%H:%M"
    )

    return (
        "15:30"
        <= now <
        "15:31"
    )