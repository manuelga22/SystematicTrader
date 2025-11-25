
from signals import TradingSignal, TradingSignalEnum
from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import Positions

DEFAULT_THRESHOLD = 0.02  # 2% loss threshold
DESCRIPTION = """Trading rule that exits trades early if a predefined loss threshold is met.\n
                 The idea of this strategy is to minimize losses by exiting a trade when the price drops.
              """

class EarlyLossTaker(TradingStrategy):

    def __init__(self, loss_threshold=DEFAULT_THRESHOLD):
        self.loss_threshold = loss_threshold
        self.description = DESCRIPTION

    def generate_signal(self, market_data: MarketData, positions_data: Positions) -> TradingSignal:
        
        if positions_data.are_we_holding_positions():
            # look for sell signals
            
            position_entry_point = positions_data.positions[0].get_entry_price()
            latest_price = market_data.get_latest_price()
            loss_percentage = (position_entry_point - latest_price) / position_entry_point
            
            # If there is loss beyond the threshold, signal to sell
            if loss_percentage >= self.loss_threshold:
                return TradingSignalEnum.SELL
            else:
                return TradingSignalEnum.NONE

        else:
    
            print("No open positions to evaluate for early loss taker.")
            return TradingSignalEnum.HOLD
            



            
           