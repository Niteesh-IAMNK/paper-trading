from shared.paper_engine import (
    buy,
    sell,
)
from shared.snapshot import invalidate_market_snapshot_cache
from shared.telegram_bot import (
    send_trade_buy,
    send_trade_sell,
)
from shared.logger import log_info


def execute_signal(
    portfolio,
    signal,
    current_price,
):
    if not signal:
        return

    action = signal.get("action")

    if action == "BUY":
        success, message, trade = buy(
            portfolio,
            signal["symbol"],
            signal["quantity"],
            current_price,
            signal.get("reason", ""),
        )

        if success:
            invalidate_market_snapshot_cache()
            log_info(
                f"{portfolio.ai_name.upper()} BUY "
                f"{signal['symbol']} x{signal['quantity']} @ {current_price}"
            )
            send_trade_buy(
                portfolio.ai_name,
                signal["symbol"],
                current_price,
                signal["quantity"],
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
            invalidate_market_snapshot_cache()
            log_info(
                f"{portfolio.ai_name.upper()} SELL "
                f"{trade.symbol} @ {current_price} "
                f"PnL {trade.pnl:+.2f}"
            )
            send_trade_sell(
                portfolio.ai_name,
                trade.symbol,
                current_price,
                trade.pnl,
                trade.reason,
                trade.timestamp,
            )
