import datetime

import pandas as pd

BUY = "BUY"
SELL = "SELL"

class PositionData:
    """
    Class for storing position data.
    """
    def __init__(self, symbol: str, quantity: float, entry_price: float, action: str, timestamp: pd.Timestamp = None):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.action = action

    def get_entry_price(self) -> float:
        return self.entry_price
    

class Positions:
    """
    Class for storing multiple position data.
    """
    def __init__(self, cash: float = 0.0):
        self.positions = []
        self.trade_history = []
        self.cash = cash

    def add_position(self, symbol: str, quantity: float, entry_price: float, timestmap: pd.Timestamp = None):
        if quantity * entry_price > self.cash:
            print("Insufficient cash to add position.")
            return
        else:
            self.cash -= quantity * entry_price
            position = PositionData(symbol, quantity, entry_price, action=BUY, timestamp=timestmap)
            self.positions.append(position)
            self.trade_history.append(position)

    def are_we_holding_positions(self) -> bool:
        return len(self.positions) > 0

    def get_available_cash(self) -> float:
        return self.cash
    
    def get_holding_time_minutes(self, current_time: pd.Timestamp) -> int:
        """Calculate holding time in minutes for the current open position(s)."""
        if not self.positions:
            return 0
        else:
            print(type(self.positions[0].timestamp), self.positions[0].timestamp)
            entry_time = pd.to_datetime(self.positions[0].timestamp, unit='ms', utc=True)
            if current_time.tzinfo is None:
                current_time = current_time.tz_localize('UTC')
            holding_time_minutes = (current_time - entry_time).total_seconds() / 60
            return holding_time_minutes
        
    def get_returns_from_trade_history(self) -> pd.DataFrame:
        """Calculate returns from trade history."""
        positions_df = self.parse_positions()
        returns = []

        for index, row in positions_df.iterrows():
            returns.append((row["sold_price"] - row["entry_price"]) / row["entry_price"])


        positions_df["returns"] = returns
        return positions_df
    
    def remove_position(self, symbol: str, current_price: float) -> PositionData:
        """
        Removes position by symbol and returns it.
        :param symbol: The symbol of the position to remove.
        :return: The removed PositionData object.
        """
        position = None
        for pos in self.positions:
            if pos.symbol == symbol:
                position = pos

        if position is None:
            print(f"No position found for symbol: {symbol}")
            return None
        
        # update current positions and trade history
        self.positions = [pos for pos in self.positions if pos.symbol != symbol]
        self.trade_history.append(PositionData(symbol, position.quantity, current_price, SELL))
        return position
        
    def show_positions(self) -> list:
        for pos in self.positions:
            print(f"Symbol: {pos.symbol}, Quantity: {pos.quantity}, Entry Price: {pos.entry_price}")
        
        if self.positions == []:
            print("No open positions.")

        return self.positions
    
    def parse_positions(self) -> pd.DataFrame:
        """Parse positions into a dataframe for easier analysis."""
        data = []
        for pos in range(0, len(self.trade_history), 2):  # Step by 2 to get buy-sell pairs
            try:
                pos_pair = self.trade_history[pos: pos + 2]
                data.append({
                    "symbol": pos_pair[0].symbol,
                    "quantity": pos_pair[0].quantity,
                    "entry_price": pos_pair[0].entry_price,
                    "sold_price": pos_pair[1].entry_price if pos_pair[1] else None,
                })
            except IndexError:
                print("Index out of range")
                continue
        
        df = pd.DataFrame(data)
        return df

    