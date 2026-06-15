from datetime import datetime
from zoneinfo import ZoneInfo

from shared.app_runner import (
    PORTFOLIOS,
    DAY_OPENING_CAPITAL
)

from shared.daily_pnl import (
    save_daily_pnl
)

from shared.telegram_bot import (
    send_message
)

IST = ZoneInfo(
    "Asia/Kolkata"
)


def generate_daily_summary():

    summary = []

    winner = None
    winner_pnl = float("-inf")

    trade_date = datetime.now(
        IST
    ).strftime(
        "%Y-%m-%d"
    )

    for ai_name, portfolio in (
        PORTFOLIOS.items()
    ):

        opening = (
            DAY_OPENING_CAPITAL.get(
                ai_name,
                500000
            )
        )

        closing = (
            portfolio.equity
        )

        pnl = round(
            closing - opening,
            2
        )

        trades = getattr(
            portfolio,
            "trade_count",
            0
        )

        save_daily_pnl(
            trade_date=trade_date,
            ai_name=ai_name,
            opening_capital=opening,
            closing_capital=closing,
            pnl=pnl,
            trades=trades
        )

        summary.append(
            {
                "name": ai_name,
                "pnl": pnl,
                "trades": trades
            }
        )

        if pnl > winner_pnl:

            winner_pnl = pnl
            winner = ai_name

    message = (
        "📊 DAILY SUMMARY\n\n"
    )

    for item in summary:

        emoji = {
            "gpt": "🤖",
            "gemini": "💎",
            "grok": "🚀"
        }.get(
            item["name"],
            "📈"
        )

        message += (
            f"{emoji} "
            f"{item['name'].upper()}\n"
            f"Trades: "
            f"{item['trades']}\n"
            f"PnL: ₹"
            f"{item['pnl']}\n\n"
        )

    if winner:

        message += (
            f"🏆 Winner: "
            f"{winner.upper()} "
            f"(₹{winner_pnl})"
        )

    return message


def send_daily_summary():

    message = (
        generate_daily_summary()
    )

    send_message(
        message
    )   