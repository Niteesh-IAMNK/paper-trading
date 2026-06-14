from shared.portfolio import create_portfolio
from shared.database import save_portfolio

for ai in ["gpt", "gemini", "grok"]:
    p = create_portfolio(ai)
    save_portfolio(p)
    print(f"Initialized {ai}: ₹{p.cash:,.0f}")