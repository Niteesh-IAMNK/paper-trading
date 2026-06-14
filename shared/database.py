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

def save_position(ai_name, position):
    conn = get_connection()
    cur = conn.cursor()

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