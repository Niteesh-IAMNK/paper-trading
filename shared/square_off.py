from shared.paper_engine import (
    sell
)


def square_off(
    portfolio,
    current_price
):

    if not portfolio.position:
        return

    sell(
        portfolio,
        current_price,
        "Auto Square Off"
    )