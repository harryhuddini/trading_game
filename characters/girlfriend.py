# characters/girlfriend.py
import random

from characters.base_character import Character
from characters.dialog_generator import generate_dialog


class Girlfriend(Character):
    name = "Girlfriend"

    def give_hint(self, hidden_state):
        drift = hidden_state["drift"]

        optimism = 0.15
        noise = random.gauss(0, 0.6)

        signal = drift + optimism + noise

        direction = "up" if signal >= 0 else "down"
        confidence = min(1.0, abs(signal))

        return {
            "direction": direction,
            "confidence": confidence,
            "text": generate_dialog(direction, confidence),
        }
