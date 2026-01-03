# characters/analyst.py
import random

from characters.base_character import Character
from characters.dialog_generator import generate_dialog


class Analyst(Character):
    name = "Analyst"

    def give_hint(self, hidden_state):
        drift = hidden_state["drift"]

        noise = random.gauss(0, 0.3)
        signal = drift + noise

        direction = "up" if signal >= 0 else "down"
        confidence = min(1.0, abs(signal) * 2)

        return {
            "direction": direction,
            "confidence": confidence,
            "text": generate_dialog(direction, confidence),
        }
