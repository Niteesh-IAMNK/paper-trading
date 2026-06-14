from shared.portfolio import create_portfolio
from shared.database import save_portfolio, get_portfolio

gpt = create_portfolio("gpt")

save_portfolio(gpt)

row = get_portfolio("gpt")

print(dict(row))