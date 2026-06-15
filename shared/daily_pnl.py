import sqlite3


DB = "data/trades.db"


def save_daily_pnl(
    trade_date,
    ai_name,
    opening_capital,
    closing_capital,
    pnl,
    trades
):

    return_pct = 0

    if opening_capital > 0:

        return_pct = (
            pnl /
            opening_capital
        ) * 100

    conn = sqlite3.connect(
        DB
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO daily_pnl
        (
            trade_date,
            ai_name,
            opening_capital,
            closing_capital,
            pnl,
            return_pct,
            trades
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            trade_date,
            ai_name,
            opening_capital,
            closing_capital,
            pnl,
            return_pct,
            trades
        )
    )

    conn.commit()
    conn.close()