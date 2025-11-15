class PositionData:
    """
    Class for storing position data.
    """
    def __init__(self, symbol: str, quantity: float, entry_price: float):
        self.timestamp = None
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price

    