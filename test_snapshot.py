from shared.market_data import refresh_indices
from shared.portfolio import create_portfolio
from shared.snapshot import build_snapshot

refresh_indices()

p = create_portfolio(
    "gpt"
)

print(
    build_snapshot(p)
)