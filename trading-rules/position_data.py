
class Positions:
    """
    Class for storing multiple position data.
    """
    def __init__(self, cash: float = 0.0):
        self.positions = []
        self.cash = cash

    def add_position(self, symbol: str, quantity: float, entry_price: float):

        if quantity * entry_price > self.cash:
            print("Insufficient cash to add position.")
            return
        else:
            self.cash -= quantity * entry_price
            position = PositionData(symbol, quantity, entry_price)
            self.positions.append(position)

    def are_we_holding_positions(self) -> bool:
        return len(self.positions) > 0

    def get_available_cash(self) -> float:
        return self.cash

class PositionData:
    """
    Class for storing position data.
    """
    def __init__(self, symbol: str, quantity: float, entry_price: float, timestamp: str = None):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price

    def get_entry_price(self) -> float:
        return self.entry_price

    