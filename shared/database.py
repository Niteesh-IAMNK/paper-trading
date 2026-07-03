import sqlite3
from pathlib import Path

DB_PATH = Path("data/trades.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ========================
# Portfolio
# ========================

def save_portfolio(portfolio):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO portfolios (
            ai_name,
            cash,
            realized_pnl,
            unrealized_pnl,
            equity
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        portfolio.ai_name,
        portfolio.cash,
        portfolio.realized_pnl,
        portfolio.unrealized_pnl,
        portfolio.equity
    ))

    conn.commit()
    conn.close()


def get_portfolio(ai_name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM portfolios
        WHERE ai_name = ?
    """, (ai_name,))

    row = cur.fetchone()

    conn.close()

    return row


# ========================
# Position
# ========================

def get_position(ai_name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT symbol, quantity, entry_price, entry_time
        FROM positions
        WHERE ai_name = ?
        ORDER BY id DESC
        LIMIT 1
    """, (ai_name,))

    row = cur.fetchone()
    conn.close()
    return row


def save_position(ai_name, position):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM positions
        WHERE ai_name = ?
    """, (ai_name,))

    cur.execute("""
        INSERT INTO positions (
            ai_name,
            symbol,
            quantity,
            entry_price,
            entry_time
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        ai_name,
        position.symbol,
        position.quantity,
        position.entry_price,
        position.entry_time.isoformat()
    ))

    conn.commit()
    conn.close()


def clear_position(ai_name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM positions
        WHERE ai_name = ?
    """, (ai_name,))

    conn.commit()
    conn.close()


# ========================
# Trades
# ========================

def save_trade(trade):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO trades (
            ai_name,
            symbol,
            action,
            quantity,
            price,
            timestamp,
            pnl,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trade.ai_name,
        trade.symbol,
        trade.action,
        trade.quantity,
        trade.price,
        trade.timestamp.isoformat(),
        trade.pnl,
        trade.reason
    ))

    conn.commit()
    conn.close()


def get_daily_trade_stats(ai_name: str, trade_date: str) -> dict:
    """
    Return daily trade statistics for one AI.

    trade_date format: YYYY-MM-DD
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            COUNT(CASE WHEN action = 'SELL' THEN 1 END) AS trades,
            COUNT(CASE WHEN action = 'SELL' AND pnl > 0 THEN 1 END) AS wins,
            COUNT(CASE WHEN action = 'SELL' AND pnl < 0 THEN 1 END) AS losses,
            COALESCE(SUM(CASE WHEN action = 'SELL' THEN pnl ELSE 0 END), 0) AS realized_pnl
        FROM trades
        WHERE ai_name = ?
          AND substr(timestamp, 1, 10) = ?
        """,
        (ai_name, trade_date),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "realized_pnl": 0.0,
        }

    return {
        "trades": row["trades"] or 0,
        "wins": row["wins"] or 0,
        "losses": row["losses"] or 0,
        "realized_pnl": float(row["realized_pnl"] or 0.0),
    }