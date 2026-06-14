from shared.portfolio import create_portfolio
from shared.trade_manager import *
from shared.paper_engine import buy

gpt = create_portfolio("gpt")

print(
    can_buy(
        gpt,
        50,
        150
    )
)

buy(
    gpt,
    "NIFTY25700CE",
    50,
    150
)

print(
    can_buy(
        gpt,
        50,
        150
    )
)

print(
    can_sell(
        gpt
    )
)

print(
    open_positions_count(
        gpt
    )
)

print(
    has_capacity(
        gpt
    )
)