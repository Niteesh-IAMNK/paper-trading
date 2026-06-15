import gpt.strategy as gpt
import gemini.strategy as gemini
import grok.strategy as grok


AIS = {
    "gpt": gpt,
    "gemini": gemini,
    "grok": grok
}


def get_signal(
    ai_name,
    snapshot
):
    strategy = AIS.get(
        ai_name
    )

    if not strategy:
        return None

    return strategy.generate_signal(
        snapshot
    )