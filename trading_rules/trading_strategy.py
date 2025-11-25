from abc import abstractmethod
from market_data import MarketData
from position_data import PositionData
from signals import TradingSignal

class TradingStrategy:
    """Base class for trading strategies."""
    def __init__(self):
        pass

    @abstractmethod
    def generate_signal(self, market_data: MarketData, positions_data: PositionData) -> TradingSignal:
        """
        Generate trading signals based on market data.

        Parameters:
        market_data (DataFrame): A DataFrame containing market data with columns such as 'price', 'volume', etc.

        Returns:
        signals (TradingSignal): An instance of TradingSignal indicating BUY, HOLD, or SELL.
        """
        pass