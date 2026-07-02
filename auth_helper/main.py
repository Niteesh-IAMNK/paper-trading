#!/usr/bin/env python3
"""
FYERS automatic login and token renewal utility.

Usage:
    python -m auth_helper.main

Or from the project root after adding auth_helper to PYTHONPATH:
    python auth_helper/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python auth_helper/main.py` from project root
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth_helper.token_manager import run_standalone


def main() -> int:
    return run_standalone()


if __name__ == "__main__":
    raise SystemExit(main())
