# simulation/galton_simulator.py
import random
import math

from simulation.base_simulator import PriceSimulator
from simulation.price_path import PricePath


class GaltonSimulator(PriceSimulator):
    def __init__(
        self,
        start_price: float = 100.0,
        pegs_per_step: int = 20,
        volatility: float = 0.25,
        drift: float = 0.0,
        time_scale: float = 1.0,
    ):
        """
        pegs_per_step : number of Bernoulli trials per step
        volatility    : annualized-like vol (game units)
        drift         : directional bias
        time_scale    : compress time (bigger = faster market)
        """
        self.start_price = start_price
        self.pegs = pegs_per_step
        self.vol = volatility
        self.drift = drift
        self.time_scale = time_scale

        self.reset()

    def reset(self):
        self.path = PricePath(self.start_price)

    def step(self, dt: float) -> float:
        """
        Galton step → binomial → normal → log-return
        """
        # --- Galton / binomial ---
        hits = 0
        for _ in range(self.pegs):
            hits += 1 if random.random() > 0.5 else -1

        # Normalize to approx N(0,1)
        z = hits / math.sqrt(self.pegs)

        # Time-scaled log return
        log_return = (
            self.drift * dt
            + self.vol * math.sqrt(dt * self.time_scale) * z
        )

        new_price = self.path.last * math.exp(log_return)
        self.path.add(new_price)

        return new_price
