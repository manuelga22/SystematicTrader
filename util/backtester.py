
import pandas as pd

from trading_rules.mean_reversal import MeanReversal, HoldingTimeEnumMinutes
from trading_rules.market_data import MarketData
from trading_rules.position_data import Positions
from trading_rules.signals import TradingSignalEnum


def perform_mean_reversal_backtest(symbol:str, 
                                   rule: MeanReversal,
                                   market_data: MarketData, 
                                   positions: Positions):

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

        signal = rule.generate_signal_buy_at_entry_sell_after_time(symbol=symbol,
                                                                   market_data=current_window_data,
                                                                   positions_data=positions,
                                                                   holding_time=HoldingTimeEnumMinutes.ONE_DAY)


        if signal.value is TradingSignalEnum.BUY.value:

            price = current_window_data.get_latest_price()
            quantity = positions.get_available_cash() // price
            if quantity > 0:
                positions.buy_position(symbol=symbol,
                                       quantity=quantity,
                                       entry_price=price,
                                       timestamp=current_window_data.get_latest_timestamp())

        elif signal.value is TradingSignalEnum.SELL.value:

            quantity = positions.stock_quantity_dict.get(symbol, 0)
            if quantity > 0:
                positions.sell_position(symbol=symbol,
                                        quantity=quantity,
                                        current_price=current_window_data.get_latest_price(),
                                        timestamp=current_window_data.get_latest_timestamp())

    return positions