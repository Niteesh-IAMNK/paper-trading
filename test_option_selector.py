from shared.option_selector import *

nifty = 23622.9

atm = get_atm_strike(
    nifty
)

print(
    "NIFTY:",
    nifty
)

print(
    "ATM:",
    atm
)

print(
    "CE +1:",
    get_otm_call(
        atm
    )
)

print(
    "PE -1:",
    get_otm_put(
        atm
    )
)