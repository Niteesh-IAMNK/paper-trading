from shared.paper_engine import (
    buy,
    sell,
)
from shared.snapshot import invalidate_market_snapshot_cache
from shared.lot_sizing import (
    format_lot_log,
    lots_to_quantity,
    resolve_lots_from_signal,
    validate_buy_quantity,
    quantity_to_lots,
)
from shared.trade_manager import can_buy
from shared.telegram_bot import (
    send_trade_buy,
    send_trade_sell,
)
from shared.logger import log_info, log_error


def execute_signal(
    portfolio,
    signal,
    current_price,
):
    if not signal:
        return

    action = signal.get("action")

    if action == "BUY":
        lots = resolve_lots_from_signal(signal)
        quantity = lots_to_quantity(lots)

        valid, message = validate_buy_quantity(quantity)
        if not valid:
            log_error(
                f"{portfolio.ai_name.upper()} BUY rejected: {message}"
            )
            return

        allowed, reason = can_buy(
            portfolio,
            quantity,
            current_price,
        )
        if not allowed:
            log_error(
                f"{portfolio.ai_name.upper()} BUY rejected: {reason}"
            )
            return

        success, buy_message, trade = buy(
            portfolio,
            signal["symbol"],
            quantity,
            current_price,
            signal.get("reason", ""),
        )

        if success:
            invalidate_market_snapshot_cache()
            log_info(
                f"{portfolio.ai_name.upper()} BUY\n"
                f"{format_lot_log(lots, quantity)}\n"
                f"Symbol   : {signal['symbol']}\n"
                f"Price    : {current_price}"
            )
            send_trade_buy(
                portfolio.ai_name,
                signal["symbol"],
                current_price,
                quantity,
                trade.timestamp if trade else None,
            )
        return

    if action == "SELL":
        success, message, trade = sell(
            portfolio,
            current_price,
            signal.get("reason", ""),
        )

        if success and trade:
            lots = quantity_to_lots(trade.quantity)
            invalidate_market_snapshot_cache()
            log_info(
                f"{portfolio.ai_name.upper()} SELL\n"
                f"{format_lot_log(lots, trade.quantity)}\n"
                f"Symbol   : {trade.symbol}\n"
                f"Price    : {current_price}\n"
                f"PnL      : {trade.pnl:+.2f}"
            )
            send_trade_sell(
                portfolio.ai_name,
                trade.symbol,
                current_price,
                trade.pnl,
                trade.reason,
                trade.timestamp,
            )
