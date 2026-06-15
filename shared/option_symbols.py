from datetime import datetime, timedelta
from .option_selector import get_atm_strike


def get_next_tuesday():
    """
    Returns the nearest Tuesday expiry date.

    Example:
    15-Jun-2026 (Mon) -> 16-Jun-2026 (Tue)
    """

    today = datetime.now()

    days_ahead = (
        1 - today.weekday()
    ) % 7

    expiry = (
        today +
        timedelta(days=days_ahead)
    )

    return expiry


def get_expiry_code():
    """
    Example:
    16-Jun-2026 -> 16JUN26
    """

    expiry = get_next_tuesday()

    return expiry.strftime(
        "%d%b%y"
    ).upper()


def build_option_symbol(
    strike: int,
    option_type: str
):
    """
    Returns:

    NSE:NIFTY16JUN2623600CE
    NSE:NIFTY16JUN2623600PE
    """

    expiry = get_expiry_code()

    return (
        f"NSE:NIFTY"
        f"{expiry}"
        f"{strike}"
        f"{option_type.upper()}"
    )


def get_atm_option_symbols(
    nifty_price: float
):
    """
    Returns ATM CE and PE symbols.

    Example:
    {
        "strike": 23600,
        "ce": "NSE:NIFTY16JUN2623600CE",
        "pe": "NSE:NIFTY16JUN2623600PE"
    }
    """

    strike = get_atm_strike(
        nifty_price
    )

    return {
        "strike": strike,

        "ce":
            build_option_symbol(
                strike,
                "CE"
            ),

        "pe":
            build_option_symbol(
                strike,
                "PE"
            )
    }