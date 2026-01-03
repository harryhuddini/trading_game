# characters/base_character.py
from abc import ABC, abstractmethod
from typing import Dict


class Character(ABC):
    name: str

    @abstractmethod
    def give_hint(self, hidden_state: Dict) -> Dict:
        """
        hidden_state example:
        {
            "drift": float,
            "volatility": float
        }

        return example:
        {
            "direction": "up" | "down",
            "confidence": float,  # 0..1
            "text": str
        }
        """
        pass
