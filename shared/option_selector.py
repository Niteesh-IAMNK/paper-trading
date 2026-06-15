from math import floor


def get_atm_strike(
    nifty_price: float
):
    """
    NIFTY strikes are in multiples of 50.
    """

    if not nifty_price:
        return None

    return round(
        nifty_price / 50
    ) * 50


def get_otm_call(
    strike: int,
    steps: int = 1
):
    return strike + (
        steps * 50
    )


def get_otm_put(
    strike: int,
    steps: int = 1
):
    return strike - (
        steps * 50
    )