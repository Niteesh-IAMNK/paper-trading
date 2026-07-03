import gpt.strategy as gpt
import gemini.strategy as gemini
import grok.strategy as grok

from shared.logger import log_error
from shared.telegram_bot import send_ai_engine_error

AIS = {
    "gpt": gpt,
    "gemini": gemini,
    "grok": grok,
}


def get_signal(ai_name, snapshot):
    strategy = AIS.get(ai_name)

    if not strategy:
        return None

    try:
        return strategy.generate_signal(snapshot)
    except Exception as exc:
        log_error(f"{ai_name.upper()} strategy error: {exc}")
        send_ai_engine_error(ai_name, str(exc))
        return {
            "action": "HOLD",
            "reason": f"Engine error: {exc}",
        }
