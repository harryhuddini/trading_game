# core/events.py
from enum import Enum, auto


class GameEvent(Enum):
    START_GAME = auto()
    END_ROUND = auto()
    BUY = auto()
    SELL = auto()
    NEXT_ROUND = auto()
    QUIT = auto()
