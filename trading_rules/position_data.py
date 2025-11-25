

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
    
    def remove_position(self, symbol: str) -> PositionData:
        """
        Removes position by symbol and returns it.
        :param symbol: The symbol of the position to remove.
        :return: The removed PositionData object.
        """
        position = None
        for pos in self.positions:
            if pos.symbol == symbol:
                position = pos
        self.positions = [pos for pos in self.positions if pos.symbol != symbol]
        return position
        
    def show_positions(self) -> list:
        for pos in self.positions:
            print(f"Symbol: {pos.symbol}, Quantity: {pos.quantity}, Entry Price: {pos.entry_price}")
        
        if self.positions == []:
            print("No open positions.")

        return self.positions

    