
from signals import TradingSignal, TradingSignalEnum
from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import PositionData

DEFAULT_THRESHOLD = 0.02  # 2% loss threshold

class EarlyLoss(TradingStrategy):
    """Trading rule that exits trades early if a predefined loss threshold is met.

    The idea of this strategy is to minimize losses by exiting a trade when the price drops
    """
    def __init__(self, loss_threshold=DEFAULT_THRESHOLD, timeframe=TimeframesEnum.ONE_HOUR, max_bars=5):
        self.timeframe = timeframe
        self.loss_threshold = loss_threshold
        self.max_bars = max_bars
        self.loss_threshold = 0.02  # 2% loss threshold

    def generate_signal(self, market_data: MarketData, positions_data: PositionData) -> TradingSignal:
        
        if positions_data.are_we_holding_positions():
            # look for sell signals
            
            position_entry_point = positions_data[0].get_entry_price()
            latest_price = market_data.get_latest_price()
            loss_percentage = (position_entry_point - latest_price) / position_entry_point
            
            # If there is loss beyond the threshold, signal to sell
            if loss_percentage >= self.loss_threshold:
                return TradingSignalEnum.SELL

        elif not positions_data.are_we_holding_positions():
            # look for buy signals

            pass
            



            
           