"""
Lot-based position sizing for the execution layer.

Strategies may optionally return ``lots``. When omitted, the engine
defaults to ``DEFAULT_LOTS`` (1 lot).
"""

from __future__ import annotations

from shared.config import DEFAULT_LOTS, LOT_SIZE


def resolve_lots_from_signal(signal: dict) -> int:
    """Resolve lot count from a strategy signal."""
    if not isinstance(signal, dict):
        return DEFAULT_LOTS

    if "lots" in signal and signal["lots"] is not None:
        try:
            lots = int(signal["lots"])
            if lots > 0:
                return lots
        except (TypeError, ValueError):
            pass

    return DEFAULT_LOTS


def lots_to_quantity(lots: int) -> int:
    """Convert lots to exchange quantity."""
    return lots * LOT_SIZE


def quantity_to_lots(quantity: int) -> int:
    """Convert quantity to whole lots (floor)."""
    if quantity <= 0:
        return 0
    return quantity // LOT_SIZE


def is_valid_lot_quantity(quantity: int) -> bool:
    """Return True when quantity is a positive multiple of LOT_SIZE."""
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
    lot_label = "lot" if lots == 1 else "lots"
    return (
        f"{lots} {lot_label}\n"
        f"Quantity : {quantity}"
    )
