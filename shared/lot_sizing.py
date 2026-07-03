"""
Lot-based position sizing for the execution layer.

Strategies return ``lots``. The engine converts to exchange quantity.
"""

from __future__ import annotations

from shared.config import DEFAULT_LOTS, LOT_SIZE


def resolve_lots_from_signal(signal: dict) -> int:
    """Resolve lot count from a strategy signal."""
    if not isinstance(signal, dict):
        return DEFAULT_LOTS

    if signal.get("lots") is not None:
        try:
            lots = int(signal["lots"])
            if lots > 0:
                return lots
        except (TypeError, ValueError):
            pass

    # Legacy compatibility: convert old quantity-based signals without changing strategies
    legacy_qty = signal.get("quantity")
    if legacy_qty is not None:
        try:
            quantity = int(legacy_qty)
            if quantity > 0:
                return max(1, quantity // LOT_SIZE)
        except (TypeError, ValueError):
            pass

    return DEFAULT_LOTS


def lots_to_quantity(lots: int) -> int:
    return lots * LOT_SIZE


def quantity_to_lots(quantity: int) -> int:
    if quantity <= 0:
        return 0
    return quantity // LOT_SIZE


def is_valid_lot_quantity(quantity: int) -> bool:
    return quantity > 0 and quantity % LOT_SIZE == 0


def validate_buy_quantity(quantity: int) -> tuple[bool, str]:
    if quantity <= 0:
        return False, "Quantity must be positive."
    if quantity % LOT_SIZE != 0:
        return (
            False,
            f"Quantity {quantity} is not a multiple of LOT_SIZE ({LOT_SIZE}).",
        )
    return True, "OK"


def format_lot_log(lots: int, quantity: int) -> str:
    label = "lot" if lots == 1 else "lots"
    return f"{lots} {label}\nQuantity : {quantity}"
