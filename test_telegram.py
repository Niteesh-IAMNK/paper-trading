from shared.telegram_bot import (
    send_trade_message
)

send_trade_message(
    ai_name="GPT",
    action="BUY",
    symbol="NIFTY25700CE",
    quantity=50,
    price=152.25,
    reason="EMA crossover"
)