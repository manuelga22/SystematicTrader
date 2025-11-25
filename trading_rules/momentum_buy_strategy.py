from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import PositionData
from signals import TradingSignalEnum, TradingSignal

class EarlyLossTaker(TradingStrategy):
    """Trading rule that exits trades early if a predefined loss threshold is met.

    The idea of this strategy is to minimize losses by exiting a trade when the price drops
    """
    def __init__(self, short_window=5, long_window=20, timeframe=TimeframesEnum.ONE_HOUR):
        self.short_window = short_window
        self.long_window = long_window
        self.timeframe = timeframe
        self.loss_threshold = 0.02  # 2% loss threshold

    def generate_signal(self, market_data: MarketData, positions_data: PositionData) -> TradingSignal:
        
        short_return = self.__get_short_return(market_data)
        long_return = self.__get_long_return(market_data)

        if long_return < short_return:
            return TradingSignalEnum.BUY
        elif long_return > short_return:
            return TradingSignalEnum.SELL
        else:
            return TradingSignalEnum.HOLD
    
    def __get_short_return(self, market_data):
        pass

    def __get_long_return(self, market_data):
        pass
    