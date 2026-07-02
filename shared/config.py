import os

from dotenv import load_dotenv

load_dotenv()

INITIAL_CAPITAL = 500000
MAX_POSITIONS = 1
BROKERAGE = 0
SLIPPAGE = 0

# NIFTY weekly options lot size (exchange standard)
LOT_SIZE = 65
DEFAULT_LOTS = 1

MARKET_OPEN = "09:15:00"
MARKET_CLOSE = "15:30:00"
AUTO_SQUARE_OFF = "15:20:00"

TIMEZONE = "Asia/Kolkata"
DATABASE_PATH = "../data/trades.db"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

LOG_LEVEL = "INFO"