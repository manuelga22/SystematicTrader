from trading_rules import mean_reversal, loss_profit_taker
from trading_rules.position_data import Positions
from trading_rules.market_data import MarketData
from trading_rules.signals import TradingSignalEnum

DEFAULT_THRESHOLD = 0.02  # 2%
DESCRIPTION = """
              Mean Reversal Strategy with Loss and Profit Taking.\n
              This strategy combines a mean reversal approach with loss and profit thresholds.
              """

class MeanReversalShield():

    def __init__(self, long_window: int, short_window: int,
                 loss_threshold: float = DEFAULT_THRESHOLD, 
                 profit_threshold: float = DEFAULT_THRESHOLD):
        super().__init__()
        self.loss_threshold = loss_threshold
        self.profit_threshold = profit_threshold
        self.long_window = long_window
        self.short_window = short_window
        self.description = DESCRIPTION

        self.buy_rule = mean_reversal.MeanReversal(short_window=self.short_window,
                                                  long_window=self.long_window)
        self.sell_rule = loss_profit_taker.LossProfitTaker(loss_threshold=self.loss_threshold,
                                                       profit_threshold=self.profit_threshold)

    def generate_signals(self, user_positions: Positions, market_data: MarketData) -> TradingSignalEnum:

        if user_positions.are_we_holding_positions():

           return self.sell_rule.generate_signal(user_positions, market_data)

        else:

           return self.buy_rule.generate_signal(user_positions, market_data)

        
