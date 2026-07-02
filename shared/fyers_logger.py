"""Logging for FYERS authentication and token renewal."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "auth.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
_LOGGER_NAME = "fyers-auth"


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = _setup_logger()


def log_info(message: str) -> None:
    logger.info(message)


def log_warning(message: str) -> None:
    logger.warning(message)


def log_error(message: str) -> None:
    logger.error(message)


def log_exception(message: str) -> None:
    logger.exception(message)
