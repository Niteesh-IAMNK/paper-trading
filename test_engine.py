from shared.portfolio import create_portfolio
from shared.paper_engine import (
    buy,
    sell,
    mark_to_market
)

gpt = create_portfolio("gpt")

print(gpt)

ok, msg, trade = buy(
    gpt,
    "NIFTY25700CE",
    50,
    150
)

print(msg)
print(gpt)

mtm = mark_to_market(
    gpt,
    165
)

print("MTM:", mtm)
print("Equity:", gpt.equity)

ok, msg, trade = sell(
    gpt,
    170
)

print(msg)
print(gpt)