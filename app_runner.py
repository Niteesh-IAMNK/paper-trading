
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from shared.fyers_token_manager import bootstrap_authentication

bootstrap_authentication()

from shared.market_data import (
    refresh_indices,
    get_market
)

from shared.snapshot import (
    build_snapshot
)

from shared.trade_executor import (
    execute_signal
)

from shared.square_off import (
    square_off
)

from shared.ai_runner import (
    get_signal
)

from shared.trading_session import (
    is_analysis_time,
    is_trading_time,
    is_square_off_time
)

from shared.summary_session import (
    is_summary_time
)

from shared.daily_summary import (
    send_daily_summary
)

from shared.portfolio import (
    create_portfolio
)

from shared.logger import (
    log_info,
    log_error
)

IST = ZoneInfo(
    "Asia/Kolkata"
)

PORTFOLIOS = {
    "gpt": create_portfolio("gpt"),
    "gemini": create_portfolio("gemini"),
    "grok": create_portfolio("grok")
}

DAY_OPENING_CAPITAL = {
    "gpt": 500000,
    "gemini": 500000,
    "grok": 500000
}

SQUARE_OFF_DONE = False
SUMMARY_DONE = False

LAST_RESET_DATE = (
    datetime.now(
        IST
    ).date()
)


def get_trade_price(
    market,
    snapshot,
    symbol
):
    """
    Returns current price
    for the given symbol.
    """

    if (
        symbol ==
        snapshot.get(
            "ce_symbol"
        )
    ):
        return snapshot.get(
            "ce_price"
        )

    if (
        symbol ==
        snapshot.get(
            "pe_symbol"
        )
    ):
        return snapshot.get(
            "pe_price"
        )

    return market.get(
        "nifty"
    )


def reset_daily_flags(
    today
):
    """
    Resets daily state.
    """

    global LAST_RESET_DATE
    global SQUARE_OFF_DONE
    global SUMMARY_DONE

    for ai_name, portfolio in (
        PORTFOLIOS.items()
    ):

        DAY_OPENING_CAPITAL[
            ai_name
        ] = (
            portfolio.equity
        )

    LAST_RESET_DATE = today

    SQUARE_OFF_DONE = False
    SUMMARY_DONE = False

    log_info(
        "New trading day detected."
    )


def analysis_cycle():
    """
    Warm up indicators.
    """

    for (
        ai_name,
        portfolio
    ) in PORTFOLIOS.items():

        snapshot = (
            build_snapshot(
                portfolio
            )
        )

        get_signal(
            ai_name,
            snapshot
        )

    log_info(
        "Analysis cycle completed."
    )


def trading_cycle(
    market
):
    """
    Execute trading signals.
    """

    for (
        ai_name,
        portfolio
    ) in PORTFOLIOS.items():

        snapshot = (
            build_snapshot(
                portfolio
            )
        )

        signal = (
            get_signal(
                ai_name,
                snapshot
            )
        )

        if not signal:
            continue

        symbol = signal.get(
            "symbol"
        )

        price = (
            get_trade_price(
                market,
                snapshot,
                symbol
            )
        )

        if price is None:
            continue

        execute_signal(
            portfolio,
            signal,
            price
        )


def square_off_cycle(
    market
):
    """
    Square off all positions.
    """

    global SQUARE_OFF_DONE

    if SQUARE_OFF_DONE:
        return

    squared_off = False

    for portfolio in (
        PORTFOLIOS.values()
    ):

        if not portfolio.position:
            continue

        snapshot = (
            build_snapshot(
                portfolio
            )
        )

        symbol = (
            portfolio.position.symbol
        )

        price = (
            get_trade_price(
                market,
                snapshot,
                symbol
            )
        )

        if price is None:
            continue

        square_off(
            portfolio,
            price
        )

        squared_off = True

    SQUARE_OFF_DONE = True

    if squared_off:

        log_info(
            "All positions squared off."
        )

    else:

        log_info(
            "No open positions to square off."
        )


def summary_cycle():
    """
    Send daily summary.
    """

    global SUMMARY_DONE

    if SUMMARY_DONE:
        return

    send_daily_summary(
        PORTFOLIOS,
        DAY_OPENING_CAPITAL
    )

    SUMMARY_DONE = True

    log_info(
        "Daily summary sent."
    )


def run_cycle():

    global LAST_RESET_DATE

    try:

        refresh_indices()

        market = (
            get_market()
        )

        today = (
            datetime.now(
                IST
            ).date()
        )

        if (
            today !=
            LAST_RESET_DATE
        ):
            reset_daily_flags(
                today
            )

        if (
            is_analysis_time()
        ):
            analysis_cycle()
            return

        if (
            is_trading_time()
        ):
            trading_cycle(
                market
            )
            return

        if (
            is_square_off_time()
        ):
            square_off_cycle(
                market
            )
            return

        if (
            is_summary_time()
        ):
            summary_cycle()
            return

    except Exception as e:

        log_error(
            f"App Runner Error: {e}"
        )


def start():

    log_info(
        "Paper Trading Engine Started."
    )

    while True:

        run_cycle()

        time.sleep(
            2
        )


if __name__ == "__main__":
    start()
