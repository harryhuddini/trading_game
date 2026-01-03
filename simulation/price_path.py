# simulation/price_path.py
class PricePath:
    def __init__(self, start_price: float):
        self.start_price = start_price
        self.prices = [start_price]

    def add(self, price: float):
        self.prices.append(price)

    @property
    def last(self):
        return self.prices[-1]

    def returns(self):
        return [
            (self.prices[i] / self.prices[i - 1] - 1)
            for i in range(1, len(self.prices))
        ]
