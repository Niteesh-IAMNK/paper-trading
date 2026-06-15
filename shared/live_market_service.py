from .market_data import refresh_indices
from .logger import logger


def update_market():
    """
    Pull latest market prices from FYERS.
    """

    try:
        market = refresh_indices()

        logger.info(
            f"NIFTY={market['nifty']} "
            f"BANKNIFTY={market['banknifty']}"
        )

    except Exception as e:
        logger.error(
            f"Market update failed: {e}"
        )