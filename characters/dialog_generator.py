# characters/dialog_generator.py
import random


UP_LINES = [
    "Feels like it's going up.",
    "I'd say buy, but don't quote me.",
    "Looks bullish today.",
    "Green candles, baby.",
]

DOWN_LINES = [
    "Something feels off.",
    "I wouldn't touch this.",
    "Looks shaky to me.",
    "Red vibes today.",
]


def generate_dialog(direction: str, confidence: float) -> str:
    if direction == "up":
        base = random.choice(UP_LINES)
    else:
        base = random.choice(DOWN_LINES)

    if confidence > 0.75:
        suffix = " I'm pretty sure."
    elif confidence > 0.5:
        suffix = " But who knows."
    else:
        suffix = " Just a gut feeling."

    return base + suffix
