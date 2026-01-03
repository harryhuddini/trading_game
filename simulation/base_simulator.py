# simulation/base_simulator.py
from abc import ABC, abstractmethod


class PriceSimulator(ABC):
    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def step(self, dt: float) -> float:
        """
        Advance simulation by dt seconds.
        Returns new price.
        """
        pass
