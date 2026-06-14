import sqlite3
from pathlib import Path

# Database location
DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)

DB_PATH = DB_DIR / "trades.db"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -------------------------
    # Portfolios
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        ai_name TEXT PRIMARY KEY,
        cash REAL NOT NULL,
        realized_pnl REAL DEFAULT 0,
        unrealized_pnl REAL DEFAULT 0,
        equity REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # -------------------------
    # Positions
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ai_name TEXT NOT NULL,
        symbol TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        entry_price REAL NOT NULL,
        entry_time TEXT NOT NULL
    )
    """)

    # -------------------------
    # Trades
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ai_name TEXT NOT NULL,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        timestamp TEXT NOT NULL,
        pnl REAL DEFAULT 0,
        reason TEXT
    )
    """)

    # -------------------------
    # Daily Summary
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        ai_name TEXT NOT NULL,
        capital REAL NOT NULL,
        pnl REAL DEFAULT 0,
        trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

    print(f"✅ Database created successfully.")
    print(f"📁 Location: {DB_PATH}")


if __name__ == "__main__":
    create_tables()