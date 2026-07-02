from shared.paper_engine import sell
from shared.snapshot import invalidate_market_snapshot_cache
from shared.telegram_bot import send_trade_sell
from shared.logger import log_info


def square_off(
    portfolio,
    current_price,
):
    if not portfolio.position:
        return

    success, message, trade = sell(
        portfolio,
        current_price,
        "Auto Square Off",
    )

    if success and trade:
        invalidate_market_snapshot_cache()
        log_info(
            f"{portfolio.ai_name.upper()} SQUARE OFF "
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
