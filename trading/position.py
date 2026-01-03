# trading/position.py
class Position:
    def __init__(self):
        self.quantity = 0.0
        self.entry_price = None

    @property
    def is_open(self):
        return self.quantity != 0

    def open(self, price: float, qty: float):
        self.entry_price = price
        self.quantity = qty

    def close(self):
        self.quantity = 0
        self.entry_price = None

    def pnl(self, price: float) -> float:
        if not self.is_open:
            return 0.0
        return self.quantity * (price - self.entry_price)
