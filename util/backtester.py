

from trading_rules.mean_reversal import MeanReversal
from trading_rules.market_data import MarketData
from trading_rules.position_data import Positions
from trading_rules.signals import TradingSignalEnum


def perform_mean_reversal_backtest(market_data: MarketData, positions: Positions):

    rule = MeanReversal()
    
    left = 0
    right = rule.lookback_window  # start after we have enough data for the long mean

    while right < len(market_data.df['close']):

        current_window = market_data.df.iloc[left: right]
        current_window_data = MarketData(current_window)
        
        signal = rule.generate_signal_z_score(current_window_data, positions)

        if signal.value is TradingSignalEnum.BUY.value:
            print(f"Buy signal at index {right}, price: {current_window_data.get_latest_price()}")
            positions.add_position("TEST", quantity=1, entry_price=current_window_data.get_latest_price())
        elif signal.value is TradingSignalEnum.SELL.value:
            print(f"Sell signal at index {right}, price: {current_window_data.get_latest_price()}")
            positions.remove_position("TEST", current_price=current_window_data.get_latest_price())


        right += 1
        left += 1

    return positions