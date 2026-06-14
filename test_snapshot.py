from shared.portfolio import create_portfolio
from shared.market_data import (
    update_index,
    update_symbol
)
from shared.snapshot import build_snapshot

gpt = create_portfolio("gpt")

update_index(
    nifty=25680,
    banknifty=57950
)

update_symbol(
    "NIFTY25700CE",
    ltp=152.25,
    volume=12000,
    oi=8500
)

snapshot = build_snapshot(gpt)

print(snapshot)