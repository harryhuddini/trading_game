# characters/dentist.py
import random

from characters.base_character import Character
from characters.dialog_generator import generate_dialog


class Dentist(Character):
    name = "Dentist"

    def give_hint(self, hidden_state):
        drift = hidden_state["drift"]

        pessimism = -0.1
        noise = random.gauss(0, 0.4)

        signal = -drift + pessimism + noise

        direction = "up" if signal >= 0 else "down"
        confidence = min(1.0, abs(signal) * 0.8)

        return {
            "direction": direction,
            "confidence": confidence,
            "text": generate_dialog(direction, confidence),
        }
