
from signals import TradingSignal, TradingSignalEnum
from trading_strategy import TradingStrategy
from timeframes import TimeframesEnum
from market_data import MarketData
from position_data import Positions

DEFAULT_THRESHOLD = 0.02  # 2% loss threshold
DESCRIPTION = """Trading rule that exits trades early if a predefined loss or profit threshold is met.\n
                 It's a hybrid of EarlyLossTaker and EarlyProfitTaker.\n
                 The idea of this rule is to SELL when the price drops below a certain loss threshold or 
                 rises above a certain profit threshold.
              """

class LossProfitTaker(TradingStrategy):

    def __init__(self, loss_threshold=DEFAULT_THRESHOLD, won_threshold=DEFAULT_THRESHOLD):
        self.loss_threshold = loss_threshold
        self.won_threshold = won_threshold
        self.description = DESCRIPTION

    def generate_signal(self, market_data: MarketData, positions_data: Positions) -> TradingSignal:
        
        if positions_data.are_we_holding_positions():
            # look for sell signals
            
            position_entry_point = positions_data.positions[0].get_entry_price()
            latest_price = market_data.get_latest_price()
            position_percentage_change = (latest_price - position_entry_point) / position_entry_point

            print(f"Profit so far: {position_percentage_change}")
            
            # If there is loss beyond the threshold, signal to sell
            if position_percentage_change <= -self.loss_threshold:
                return TradingSignalEnum.SELL
            elif position_percentage_change >= self.won_threshold:
                return TradingSignalEnum.SELL
            else:
                return TradingSignalEnum.NONE

        else:
    
            print("No open positions to evaluate for early loss taker.")
            return TradingSignalEnum.NONE
            



            
           