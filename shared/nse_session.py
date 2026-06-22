import requests

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/137.0 Safari/537.36"
            ),

        "Accept":
            "application/json",

        "Accept-Language":
            "en-US,en;q=0.9",

        "Referer":
            "https://www.nseindia.com/",

        "Connection":
            "keep-alive"
    }
)


def refresh_session():
    """
    Refresh NSE cookies.
    """

    SESSION.get(
        "https://www.nseindia.com",
        timeout=10
    )

    return SESSION


def get_session():
    """
    Returns NSE session.
    """

    return SESSION