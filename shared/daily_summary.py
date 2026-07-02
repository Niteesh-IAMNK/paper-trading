from datetime import datetime
from zoneinfo import ZoneInfo

from shared.daily_pnl import save_daily_pnl
from shared.database import get_daily_trade_stats
from shared.telegram_bot import send_daily_summary_message
from shared.config import TIMEZONE

IST = ZoneInfo(TIMEZONE)


def _format_currency(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}₹{abs(value):,.2f}"


def generate_daily_summary(
    portfolios,
    opening_capital,
):
    """
    Generates per-AI daily summary messages.
    """
    summaries = []
    trade_date = datetime.now(IST).strftime("%Y-%m-%d")

    for ai_name, portfolio in portfolios.items():
        opening = opening_capital.get(ai_name, 500000)
        closing = portfolio.equity
        stats = get_daily_trade_stats(ai_name, trade_date)

        save_daily_pnl(
            trade_date=trade_date,
            ai_name=ai_name,
            opening_capital=opening,
            closing_capital=closing,
            pnl=round(closing - opening, 2),
            trades=stats["trades"],
        )

        message = (
            f"{ai_name.upper()}\n\n"
            f"Trades : {stats['trades']}\n"
            f"Wins : {stats['wins']}\n"
            f"Losses : {stats['losses']}\n"
            f"Realized PnL : {_format_currency(stats['realized_pnl'])}\n"
            f"Ending Capital : ₹{closing:,.2f}"
        )
        summaries.append(message)

    return summaries


def send_daily_summary(
    portfolios,
    opening_capital,
):
    """
    Sends one Telegram daily summary per AI.
    """
    for message in generate_daily_summary(portfolios, opening_capital):
        send_daily_summary_message(message)
