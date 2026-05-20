from dataclasses import dataclass
import pandas as pd


BUY = "BUY"
SELL = "SELL"

@dataclass
class PositionData:
    """
    Class for storing position data.
    Params:
       quantity (int): number of securities.
       entry_price (float): buying or selling price for security.
       action (str): BUY or SELL.
       cash_balance (float): cash balance left in portfolio after the current Position.
       timestamp (pd.Timestamp): time that the transaction took place.
    """
    def __init__(self, symbol: str, 
                 quantity: float, # number of stocks
                 entry_price: float, 
                 action: str,
                 cash_balance: float, # cash balance after buying or selling
                 timestamp: pd.Timestamp = None):
        self.timestamp = timestamp
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.cash_balance = cash_balance
        self.action = action

    def get_entry_price(self) -> float:
        return self.entry_price
    
    def get_symbol(self) -> str:
        return self.symbol
    
    def get_quantity(self) -> float:
        return self.quantity
    
    def get_action(self) -> str:
        return self.action
    
    def get_timestamp(self) -> pd.Timestamp:
        return self.timestamp
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "actions": self.action,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "cash_balance": self.cash_balance
        }
    
    

class Positions:
    """
    Class for storing multiple position data.
    """
    def __init__(self, cash: float = 0.0):
        self.positions_stack = []

        # keep track of how much stock we own
        self.stock_quantity_dict = {}

        self.cash = cash

    def buy_position(self, symbol: str, quantity: float, entry_price: float, timestamp: pd.Timestamp = None):
        # Check if we have enough cash to add the position
        if quantity * entry_price > self.cash:
            raise ValueError("Insufficient cash to add position.")
        else:
            self.cash -= quantity * entry_price
            position = PositionData(symbol, quantity, entry_price, action=BUY, 
                                    cash_balance=self.cash, timestamp=timestamp)
            self.positions_stack.append(position)
            self.stock_quantity_dict[symbol] = self.stock_quantity_dict.get(symbol, 0) + quantity

    def sell_position(self, symbol: str, quantity: int, current_price: float, timestamp: pd.Timestamp = None):
        """
        Removes position by symbol and returns it.
        :param symbol: The symbol of the position to remove.
        :return: The removed PositionData object.
        """
        if self.stock_quantity_dict.get(symbol) is None:
            raise ValueError(f"We do not currently own {symbol} so it can't be sold")

        if quantity > self.stock_quantity_dict.get(symbol):
            raise ValueError(f"we don't own enough {symbol} to be able to sell {quantity}, we own {quantity.get(symbol)}")

        # put back cash into account
        self.cash += (quantity * current_price)
        # update current positions and trade history
        self.positions_stack.append(PositionData(symbol, quantity, current_price, action=SELL,
                                                 cash_balance=self.cash, timestamp=timestamp))
        self.stock_quantity_dict[symbol] -= quantity


    def are_we_holding_positions(self) -> bool:
        for key, holding in self.stock_quantity_dict.items():
            if holding > 0:
                return True
        return False

    def get_available_cash(self) -> float:
        return self.cash
    
    def get_transaction_history(self) -> list[PositionData]:
        return self.positions_stack
    
    def get_holding_time_minutes(self, symbol: str, current_time_timestamp: pd.Timestamp) -> int:
        """Calculate holding time in minutes for the current open position(s).
        This will give you the holding time of the oldest transaction for a given stock.
        """

        if self.stock_quantity_dict.get(symbol) is None or self.stock_quantity_dict.get(symbol) == 0:
            raise ValueError(f"We do not currently own {symbol} so it can't be sold")

        if type(current_time_timestamp) is not pd.Timestamp:
            raise ValueError("current_time_timestamp must be a pandas Timestamp")
        
        oldest_transaction = None
        for transactions in self.positions_stack:
            if transactions.symbol == symbol:
                oldest_transaction = transactions
                break

        if oldest_transaction is None:
            raise Exception(f"Transaction not found for {symbol}")


        holding_time_minutes = (current_time_timestamp - oldest_transaction.timestamp).total_seconds() / 60
        return holding_time_minutes
        
    def get_returns_from_trade_history(self) -> pd.DataFrame:
        """Calculate returns from trade history."""
        positions_df = self.parse_positions()
        returns = []

        for _, row in positions_df.iterrows():
            returns.append((row["sold_price"] - row["entry_price"]) / row["entry_price"])

        positions_df["returns"] = returns
        return positions_df
    
    def get_holdings_at_time(self, ts: pd.Timestamp) -> dict:

        holding_dict = {}

        for pos in self.positions_stack:
            if pos.get_timestamp() <= ts:

                sym = pos.get_symbol()
                if pos.get_action() == BUY:
                    holding_dict[sym] = holding_dict.get(sym, 0) + pos.get_quantity()
                else:
                    holding_dict[sym] = holding_dict.get(sym, 0) - pos.get_quantity()
            else:
                break

        return holding_dict

        
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
                    "entry_timestamp": pos_pair[0].timestamp,
                    "exit_timestamp": pos_pair[1].timestamp if pos_pair[1] else None,
                })
            except IndexError:
                print("Index out of range")
                continue

        df = pd.DataFrame(data)
        return df

    