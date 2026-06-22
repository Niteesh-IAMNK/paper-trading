
import logging
from pathlib import Path

LOG_DIR = Path("data/logs")

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_FILE = (
    LOG_DIR /
    "app.log"
)

logger = logging.getLogger(
    "stock-test"
)

logger.setLevel(
    logging.INFO
)

if not logger.handlers:

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        LOG_FILE
    )

    file_handler.setFormatter(
        formatter
    )

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        file_handler
    )

    logger.addHandler(
        console_handler
    )

logger.propagate = False


def log_info(message):
    logger.info(message)


def log_warning(message):
    logger.warning(message)


def log_error(message):
    logger.error(message)


def log_exception(message):
    logger.exception(message)

