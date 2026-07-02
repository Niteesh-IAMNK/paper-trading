
import sys
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
    begin_snapshot_cycle,
    build_snapshot,
    get_shared_market_context,
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

from shared.engine_scheduler import (
    SESSION_BEFORE_MARKET,
    SESSION_ANALYSIS,
    SESSION_TRADING,
    SESSION_SQUARE_OFF,
    SESSION_DAILY_SUMMARY,
    SESSION_SHUTDOWN,
    compute_sleep_seconds,
    get_session,
    should_fetch_market_data,
)

from shared.signal_adapter import prepare_execution_signal
from shared.config import INITIAL_CAPITAL

IST = ZoneInfo(
    "Asia/Kolkata"
)

PORTFOLIOS = {
    "gpt": create_portfolio("gpt"),
    "gemini": create_portfolio("gemini"),
    "grok": create_portfolio("grok")
}

DAY_OPENING_CAPITAL = {
    "gpt": INITIAL_CAPITAL,
    "gemini": INITIAL_CAPITAL,
    "grok": INITIAL_CAPITAL,
}

SQUARE_OFF_DONE = False
SUMMARY_DONE = False
WAITING_LOGGED = False

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


def analysis_cycle(shared_context):
    """
    Warm up indicators.
    """

    for (
        ai_name,
        portfolio
    ) in PORTFOLIOS.items():

        snapshot = (
            build_snapshot(
                portfolio,
                shared_context,
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
    market,
    shared_context,
):
    """
    Execute trading signals.
    """

    for (
        ai_name,
        portfolio
    ) in PORTFOLIOS.items():

        try:
            snapshot = (
                build_snapshot(
                    portfolio,
                    shared_context,
                )
            )

            signal = get_signal(ai_name, snapshot)
            if not signal:
                continue

            prepared = prepare_execution_signal(signal, snapshot)
            if not prepared:
                continue

            if prepared.get("action") == "REJECTED":
                execute_signal(portfolio, prepared, 0)
                continue

            symbol = prepared.get("symbol")
            price = get_trade_price(market, snapshot, symbol)
            if price is None:
                continue

            execute_signal(portfolio, prepared, price)

        except Exception as exc:
            log_error(
                f"{ai_name.upper()} trading cycle error: {exc}"
            )


def square_off_cycle(
    market,
    shared_context,
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
                portfolio,
                shared_context,
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


def _prepare_market_context():
    refresh_indices()
    begin_snapshot_cycle()
    return get_shared_market_context()


def _run_active_session(session, shared_context=None):
    global LAST_RESET_DATE

    today = datetime.now(IST).date()
    if today != LAST_RESET_DATE:
        reset_daily_flags(today)

    if shared_context is None:
        shared_context = _prepare_market_context()

    market = get_market()

    if session == SESSION_ANALYSIS:
        log_info("Analysis session running.")
        analysis_cycle(shared_context)
        return

    if session == SESSION_TRADING:
        trading_cycle(market, shared_context)
        return

    if session == SESSION_SQUARE_OFF:
        log_info("Square-off session running.")
        square_off_cycle(market, shared_context)
        return

    if session == SESSION_DAILY_SUMMARY:
        log_info("Daily summary session running.")
        summary_cycle()
        return


def _graceful_shutdown():
    log_info("Trading day completed successfully.")
    log_info("Shutting down.")
    sys.exit(0)


def start():
    """
    Run one complete trading day, then exit with code 0.
    """
    global WAITING_LOGGED
    global SQUARE_OFF_DONE
    global SUMMARY_DONE

    log_info("Paper Trading Engine Started.")

    while True:
        now = datetime.now(IST)
        session = get_session(now)

        if session == SESSION_SHUTDOWN:
            if not SUMMARY_DONE:
                summary_cycle()
            break

        if session == SESSION_BEFORE_MARKET:
            if not WAITING_LOGGED:
                log_info("Waiting for market open...")
                WAITING_LOGGED = True
            time.sleep(compute_sleep_seconds(session, now))
            continue

        WAITING_LOGGED = False

        shared_context = None
        if should_fetch_market_data(session):
            shared_context = _prepare_market_context()

        if session == SESSION_ANALYSIS:
            _run_active_session(session, shared_context)

        elif session == SESSION_TRADING:
            _run_active_session(session, shared_context)

        elif session == SESSION_SQUARE_OFF:
            if not SQUARE_OFF_DONE:
                _run_active_session(session, shared_context)

        elif session == SESSION_DAILY_SUMMARY:
            if not SUMMARY_DONE:
                _run_active_session(session, shared_context)
                break

        time.sleep(compute_sleep_seconds(session, now))

    _graceful_shutdown()


if __name__ == "__main__":
    start()
