# trading/settlement.py
def settle(trader, final_price: float):
    if trader.position.is_open:
        trader.sell(final_price)

    return trader.balance
