from shared.fyers_auth import get_fyers

fyers = get_fyers()


def get_atm_options():
    """
    Returns:
    {
        'nifty': 23622.9,
        'strike': 23600,
        'ce': 'NSE:NIFTY2661623600CE',
        'pe': 'NSE:NIFTY2661623600PE'
    }
    """

    data = {
        "symbol": "NSE:NIFTY50-INDEX",
        "strikecount": 1
    }

    response = fyers.optionchain(
        data
    )

    if response.get("s") != "ok":
        return None

    chain = (
        response
        .get("data", {})
        .get("optionsChain", [])
    )

    if not chain:
        return None

    nifty = (
        response
        .get("data", {})
        .get("ltp")
    )

    if not nifty:
        nifty = (
            chain[0]
            .get("ltp")
        )

    strike = (
        round(
            float(nifty) / 50
        ) * 50
    )

    ce = None
    pe = None

    for item in chain:

        if (
            item.get(
                "strike_price"
            ) != strike
        ):
            continue

        symbol = item.get(
            "symbol"
        )

        option_type = (
            item.get(
                "option_type"
            )
        )

        if option_type == "CE":
            ce = symbol

        elif option_type == "PE":
            pe = symbol

    return {
        "nifty": nifty,
        "strike": strike,
        "ce": ce,
        "pe": pe
    }