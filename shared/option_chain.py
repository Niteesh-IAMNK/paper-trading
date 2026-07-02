import time

from shared.fyers_auth import get_fyers

OPTION_CHAIN_TTL_SECONDS = 5.0
_CHAIN_CACHE: dict = {
    "timestamp": 0.0,
    "data": None,
}
_FORCE_REFRESH = False


def _atm_strike_from_nifty(nifty: float) -> int:
    return int(round(float(nifty) / 50) * 50)


def invalidate_option_chain_cache() -> None:
    """Force the next option-chain request to refresh immediately."""
    global _FORCE_REFRESH
    _FORCE_REFRESH = True
    _CHAIN_CACHE["timestamp"] = 0.0
    _CHAIN_CACHE["data"] = None


def get_atm_options(force: bool = False):
    """
    Returns ATM weekly options with a 5-second shared cache.

    {
        'nifty': 23622.9,
        'strike': 23600,
        'ce': 'NSE:NIFTY2661623600CE',
        'pe': 'NSE:NIFTY2661623600PE'
    }
    """
    global _FORCE_REFRESH

    now = time.time()
    cache_age = now - _CHAIN_CACHE["timestamp"]
    cached = _CHAIN_CACHE["data"]

    if (
        not force
        and not _FORCE_REFRESH
        and cached is not None
        and cache_age < OPTION_CHAIN_TTL_SECONDS
    ):
        return cached

    fyers = get_fyers()
    data = {
        "symbol": "NSE:NIFTY50-INDEX",
        "strikecount": 1,
    }

    response = fyers.optionchain(data)

    if response.get("s") != "ok":
        message = str(response.get("message", "")).lower()
        if "429" in message or "request limit" in message:
            log_warning(
                "FYERS option chain rate limited — using cached values if available"
            )
            if cached is not None:
                return cached
        log_error(f"FYERS option chain request failed: {response.get('message')}")
        return cached

    chain = response.get("data", {}).get("optionsChain", [])
    if not chain:
        return cached

    nifty = response.get("data", {}).get("ltp")
    if not nifty:
        nifty = chain[0].get("ltp")

    strike = _atm_strike_from_nifty(nifty)

    ce = None
    pe = None

    for item in chain:
        if item.get("strike_price") != strike:
            continue

        symbol = item.get("symbol")
        option_type = item.get("option_type")

        if option_type == "CE":
            ce = symbol
        elif option_type == "PE":
            pe = symbol

    result = {
        "nifty": nifty,
        "strike": strike,
        "ce": ce,
        "pe": pe,
    }

    _CHAIN_CACHE["timestamp"] = now
    _CHAIN_CACHE["data"] = result
    _FORCE_REFRESH = False
    return result


def refresh_option_chain_if_strike_changed(nifty: float | None) -> None:
    """Invalidate cache when the ATM strike would change."""
    if nifty is None:
        return

    cached = _CHAIN_CACHE["data"]
    if not cached:
        return

    expected_strike = _atm_strike_from_nifty(nifty)
    if cached.get("strike") != expected_strike:
        invalidate_option_chain_cache()
