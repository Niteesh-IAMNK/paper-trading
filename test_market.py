
from shared.market_data import *

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

print(get_nifty())
print(get_banknifty())
print(get_ltp("NIFTY25700CE"))
print(get_symbol("NIFTY25700CE"))
print(get_market_data())