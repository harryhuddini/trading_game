from trading.position import Position
class Trader:
    def __init__(self, balance: float):
        self.balance = balance
        self.bet_size = 1000.0
        self.position = Position()

        self.realized_pnl = 0.0

    def buy(self, price: float) -> bool:
        if self.position.is_open:
            return False
        qty = self.bet_size / price
        self.position.open(price, qty)
        return True

    def sell(self, price: float) -> bool:
        if not self.position.is_open:
            return False
        pnl = self.position.pnl(price)
        self.realized_pnl += pnl
        self.balance += pnl
        self.position.close()
        return True

    def mark_to_market(self, price: float) -> float:
        if not self.position.is_open:
            return 0.0
        return self.position.pnl(price)

    def reset_round(self):
        self.realized_pnl = 0.0
