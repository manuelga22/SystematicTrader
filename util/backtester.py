
import pandas as pd

from trading_rules.mean_reversal import MeanReversal, HoldingTimeEnumMinutes
from trading_rules.market_data import MarketData
from trading_rules.position_data import Positions
from trading_rules.signals import TradingSignalEnum


def perform_mean_reversal_backtest(rule: MeanReversal, market_data: MarketData, positions: Positions):

    index = market_data.df.index

    for i in range(len(index)):

        right_ts = index[i]
        left_ts = right_ts - pd.Timedelta(days=rule.lookback_window)

        # Skip until we have a full window worth of history
        if index[0] > left_ts:
            continue

        start_ts = index.searchsorted(left_ts)
        current_window = market_data.df.iloc[start_ts: i + 1]
        current_window_data = MarketData(current_window)

        signal = rule.generate_signal_buy_at_entry_sell_after_time(current_window_data,
                                                                   positions,
                                                                   holding_time=HoldingTimeEnumMinutes.ONE_DAY)

        if signal.value is TradingSignalEnum.BUY.value:
            positions.buy_position("TEST", quantity=1, entry_price=current_window_data.get_latest_price(), timestmap=current_window_data.df.index[-1])
        elif signal.value is TradingSignalEnum.SELL.value:
            positions.sell_position("TEST", current_price=current_window_data.get_latest_price(), timestamp=current_window_data.get_latest_timestamp())

    return positions