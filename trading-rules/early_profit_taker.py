
from signals import TradingSignal, TradingSignalEnum
from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import PositionData

DEFAULT_THRESHOLD = 0.02  # 2% profit threshold
DESCRIPTION = """Trading rule that exits trades early if a predefined profit threshold is met.\n
                 The idea of this strategy is to minimize losses by exiting a trade when the price drops.
              """

class EarlyProfitTaker(TradingStrategy):

    def __init__(self, profit_threshold=DEFAULT_THRESHOLD, timeframe=TimeframesEnum.ONE_HOUR):
        self.timeframe = timeframe
        self.profit_threshold = profit_threshold  # 2% profit threshold
        self.description = DESCRIPTION

    def generate_signal(self, market_data: MarketData, positions_data: PositionData) -> TradingSignal:
        
        if positions_data.are_we_holding_positions():
            # look for sell signals
            
            position_entry_point = positions_data[0].get_entry_price()
            latest_price = market_data.get_latest_price()
            profit_percentage = (latest_price - position_entry_point) / position_entry_point

            # If there is loss beyond the threshold, signal to sell
            if profit_percentage >= self.profit_threshold:
                return TradingSignalEnum.SELL

        else:
    
            print("No open positions to evaluate for early profit taker.")
            return TradingSignalEnum.HOLD
            



            
           