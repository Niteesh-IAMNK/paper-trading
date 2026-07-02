import time

from shared.fyers_auth import get_fyers
from shared.fyers_logger import log_error, log_warning

QUOTES_TTL_SECONDS = 1.0
_QUOTES_CACHE: dict = {
    "timestamp": 0.0,
    "response": None,
    "symbols": set(),
}


def _is_rate_limited(response: dict | None) -> bool:
    if not isinstance(response, dict):
        return False

    message = str(response.get("message", "")).lower()
    code = response.get("code")
    return (
        code == 429
        or "429" in message
        or "request limit" in message
        or "rate limit" in message
    )


def _merge_symbols(symbols: list[str]) -> list[str]:
    return list(dict.fromkeys(symbols))


def get_quotes(symbols: list, force: bool = False):
    """
    Get live quotes from FYERS with a 1-second shared cache.
    """
    symbols = _merge_symbols(symbols)
    now = time.time()
    cache_age = now - _QUOTES_CACHE["timestamp"]

    if (
        not force
        and _QUOTES_CACHE["response"] is not None
        and cache_age < QUOTES_TTL_SECONDS
        and set(symbols).issubset(_QUOTES_CACHE["symbols"])
    ):
        return _filter_cached_response(symbols)

    fetch_symbols = _merge_symbols(
        list(_QUOTES_CACHE["symbols"]) + symbols
        if (
            not force
            and _QUOTES_CACHE["response"] is not None
            and cache_age < QUOTES_TTL_SECONDS
        )
        else symbols
    )

    fyers = get_fyers()
    response = fyers.quotes({"symbols": ",".join(fetch_symbols)})

    if _is_rate_limited(response):
        log_warning("FYERS quotes rate limited — using cached values if available")
        if _QUOTES_CACHE["response"] is not None:
            return _filter_cached_response(symbols)
        log_error("FYERS quotes rate limited with no cache available")
        return response

    if response.get("s") == "ok":
        _QUOTES_CACHE["timestamp"] = now
        _QUOTES_CACHE["response"] = response
        _QUOTES_CACHE["symbols"] = set(fetch_symbols)

    return _filter_cached_response(symbols)


def _filter_cached_response(symbols: list[str]):
    response = _QUOTES_CACHE["response"]
    if not isinstance(response, dict) or response.get("s") != "ok":
        return response

    wanted = set(symbols)
    filtered = []

    for item in response.get("d", []):
        if item.get("n") in wanted:
            filtered.append(item)

    return {
        "s": "ok",
        "d": filtered,
    }


def get_ltp(symbol: str, force: bool = False):
    """Returns LTP of one symbol."""
    if not symbol:
        return None

    response = get_quotes([symbol], force=force)

    if response.get("s") != "ok":
        return None

    try:
        return response["d"][0]["v"]["lp"]
    except Exception:
        return None


def get_multiple_ltps(symbols: list, force: bool = False):
    """Returns {symbol: ltp} for all requested symbols."""
    result = {}
    response = get_quotes(symbols, force=force)

    if response.get("s") != "ok":
        return result

    try:
        for item in response["d"]:
            symbol = item["n"]
            ltp = item["v"]["lp"]
            result[symbol] = ltp
    except Exception:
        pass

    return result


def invalidate_quotes_cache() -> None:
    """Clear the shared quotes cache."""
    _QUOTES_CACHE["timestamp"] = 0.0
    _QUOTES_CACHE["response"] = None
    _QUOTES_CACHE["symbols"] = set()
