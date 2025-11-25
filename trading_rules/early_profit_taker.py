
from signals import TradingSignal, TradingSignalEnum
from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import Positions

DEFAULT_THRESHOLD = 0.02  # 2% profit threshold
DESCRIPTION = """Trading rule that exits trades early if a predefined profit threshold is met.\n
                 The idea of this strategy is to minimize losses by exiting a trade when the price drops.
              """

class EarlyProfitTaker(TradingStrategy):

    def __init__(self, profit_threshold=DEFAULT_THRESHOLD):
        self.profit_threshold = profit_threshold  # 2% profit threshold
        self.description = DESCRIPTION

    def generate_signal(self, market_data: MarketData, positions_data: Positions) -> TradingSignal:
        
        if positions_data.are_we_holding_positions():
            # look for sell signals
            
            # NOTE: Our rules only support one position at a time for now
            position_entry_point = positions_data.positions[0].get_entry_price()
            latest_price = market_data.get_latest_price()
            profit_percentage = (latest_price - position_entry_point) / position_entry_point

            print(f"Profit so far: {profit_percentage}")

            # If there is loss beyond the threshold, signal to sell
            if profit_percentage >= self.profit_threshold:
                return TradingSignalEnum.SELL
            else:
                return TradingSignalEnum.NONE

        else:
    
            print("No open positions to evaluate for early profit taker.")
            return TradingSignalEnum.NONE
            



            
           