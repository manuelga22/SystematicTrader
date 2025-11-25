from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import PositionData
from signals import TradingSignalEnum, TradingSignal

class MeanReversal(TradingStrategy):
    DESCRIPTION = """Trading rule that identifies mean reversion opportunities based on price deviations from a moving average.\n
                     The idea of this strategy is to buy when the price is significantly below the moving average and sell when it is above.
                  """
    
    def __init__(self, short_window=5, long_window=20, timeframe=TimeframesEnum.ONE_HOUR):
        self.short_window = short_window
        self.long_window = long_window
        self.timeframe = timeframe

    def generate_signal(self, market_data: MarketData, positions_data: PositionData) -> TradingSignal:

        if not positions_data.are_we_holding_positions():
            # look for buy signals
            
            short_mean = self.get_short_mean(market_data)
            long_mean = self.get_long_mean(market_data)
            
            # If short mean is below long mean, signal to buy (we expect price to revert to the mean)
            if short_mean < long_mean:
                return TradingSignalEnum.BUY
        

    def get_long_mean(self, market_data):
        return market_data.get_mean(self.long_window)

    def get_short_mean(self, market_data):
        return market_data.get_mean(self.short_window)