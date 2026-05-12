
from trading_rules.mean_reversal import MeanReversal, HoldingTimeEnumMinutes
from trading_rules.market_data import MarketData
from trading_rules.position_data import Positions
from trading_rules.signals import TradingSignalEnum


def perform_mean_reversal_backtest(market_data: MarketData, positions: Positions):

    rule = MeanReversal(lookback_window=5, entry_z_threshold_entry=1.0, exit_z_threshold=0.5)
    
    left = 0
    right = rule.lookback_window  # start after we have enough data for the long mean

    while right < len(market_data.df['close']):

        current_window = market_data.df.iloc[left: right]
        current_window_data = MarketData(current_window)
        
        signal = rule.generate_signal_buy_at_entry_sell_after_time(current_window_data, positions, holding_time=HoldingTimeEnumMinutes.ONE_DAY)


        if signal.value is TradingSignalEnum.BUY.value:
            print(f"Buy signal at index {right}, price: {current_window_data.get_latest_price()}")
            positions.add_position("TEST", quantity=1, entry_price=current_window_data.get_latest_price(), timestmap=current_window_data.df.index[-1])
        elif signal.value is TradingSignalEnum.SELL.value:
            print(f"Sell signal at index {right}, price: {current_window_data.get_latest_price()}")
            positions.remove_position("TEST", current_price=current_window_data.get_latest_price())


        right += 1
        left += 1

    return positions