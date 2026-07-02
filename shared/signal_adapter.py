"""
Normalize strategy signals for the execution layer.

Strategies return BUY / SELL / HOLD and lots (for BUY).
The engine resolves symbols, converts lots to quantity, and executes.
"""

from __future__ import annotations

from shared.lot_sizing import (
    lots_to_quantity,
    resolve_lots_from_signal,
    validate_buy_quantity,
)


def resolve_trade_symbol(signal: dict, snapshot: dict) -> str | None:
    """Map a strategy signal to the tradable option symbol."""
    symbol = signal.get("symbol")
    if symbol:
        return symbol

    option_type = str(signal.get("option_type", "")).upper()
    if option_type == "CE":
        return snapshot.get("ce_symbol")
    if option_type == "PE":
        return snapshot.get("pe_symbol")

    return None


def prepare_execution_signal(signal: dict, snapshot: dict) -> dict | None:
    """
    Convert a raw strategy signal into an execution-ready payload.

    Returns None for HOLD / invalid signals.
    """
    if not isinstance(signal, dict):
        return None

    action = str(signal.get("action", "HOLD")).upper()
    reason = str(signal.get("reason", ""))

    if action == "HOLD":
        return None

    if action == "SELL":
        symbol = resolve_trade_symbol(signal, snapshot)
        if not symbol:
            return None
        return {
            "action": "SELL",
            "symbol": symbol,
            "reason": reason,
        }

    if action == "BUY":
        symbol = resolve_trade_symbol(signal, snapshot)
        if not symbol:
            return None

        lots = resolve_lots_from_signal(signal)
        quantity = lots_to_quantity(lots)
        valid, message = validate_buy_quantity(quantity)
        if not valid:
            return {
                "action": "REJECTED",
                "symbol": symbol,
                "reason": message,
            }

        return {
            "action": "BUY",
            "symbol": symbol,
            "lots": lots,
            "quantity": quantity,
            "reason": reason,
        }

    return None
