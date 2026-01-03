# core/game_state.py
from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    CONSULT = auto()
    ROUND = auto()
    RESULT = auto()
    EXIT = auto()
