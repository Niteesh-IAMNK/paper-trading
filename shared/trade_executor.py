from shared.paper_engine import (
    buy,
    sell
)


def execute_signal(
    portfolio,
    signal,
    current_price
):

    if not signal:
        return

    action = signal.get(
        "action"
    )

    if action == "BUY":

        buy(
            portfolio,
            signal["symbol"],
            signal["quantity"],
            current_price,
            signal.get(
                "reason",
                ""
            )
        )

    elif action == "SELL":

        sell(
            portfolio,
            current_price,
            signal.get(
                "reason",
                ""
            )
        )