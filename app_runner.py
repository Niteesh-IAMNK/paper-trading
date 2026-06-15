import time

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

from shared.portfolio import (
    create_portfolio
)

from shared.logger import (
    log_info,
    log_error
)


from shared.summary_session import (
    is_summary_time
)

from shared.daily_summary import (
    send_daily_summary
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

from datetime import datetime
from zoneinfo import ZoneInfo


IST = ZoneInfo(
    "Asia/Kolkata"
)

SQUARE_OFF_DONE = False
LAST_RESET_DATE = (
    datetime.now(
        IST
    ).date()
)

def run_cycle():

    global SQUARE_OFF_DONE
    global SUMMARY_DONE
    global LAST_RESET_DATE

    try:

        # Refresh market data
        refresh_indices()

        market = get_market()
        today = (
            datetime.now(
                IST
            ).date()
        )



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

        # During analysis period
        if is_analysis_time():

            for ai_name, portfolio in PORTFOLIOS.items():

                snapshot = build_snapshot(
                    portfolio
                )

                # Warm up indicators only
                get_signal(
                    ai_name,
                    snapshot
                )

            log_info(
                "Analysis cycle completed."
            )

            return

        # Trading period
        # Trading period
        if is_trading_time():

            for ai_name, portfolio in PORTFOLIOS.items():

                snapshot = build_snapshot(
                    portfolio
                )

                signal = get_signal(
                    ai_name,
                    snapshot
                )

                if not signal:
                    continue

                symbol = signal.get(
                    "symbol"
                )

                price = None

                if (
                    symbol ==
                    snapshot.get(
                        "ce_symbol"
                    )
                ):
                    price = snapshot.get(
                        "ce_price"
                    )

                elif (
                    symbol ==
                    snapshot.get(
                        "pe_symbol"
                    )
                ):
                    price = snapshot.get(
                        "pe_price"
                    )

                else:
                    price = market.get(
                        "nifty"
                    )

                if price is None:
                    continue

                execute_signal(
                    portfolio,
                    signal,
                    price
                )

            return

        # Square-off period
        # Square-off period
        if is_square_off_time():

            if SQUARE_OFF_DONE:
                return

            squared_off = False

            for portfolio in PORTFOLIOS.values():

                if not portfolio.position:
                    continue

                snapshot = build_snapshot(
                    portfolio
                )

                symbol = (
                    portfolio.position.symbol
                )

                price = None

                if (
                    symbol ==
                    snapshot.get(
                        "ce_symbol"
                    )
                ):
                    price = snapshot.get(
                        "ce_price"
                    )

                elif (
                    symbol ==
                    snapshot.get(
                        "pe_symbol"
                    )
                ):
                    price = snapshot.get(
                        "pe_price"
                    )

                else:
                    price = market.get(
                        "nifty"
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

            return
        
        # Daily summary period
        if is_summary_time():

            if SUMMARY_DONE:
                return

            send_daily_summary()

            SUMMARY_DONE = True

            log_info(
                "Daily summary sent."
            )

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

        time.sleep(2)