import unittest
import pandas as pd

from trading_rules.market_data import MarketData
from trading_rules.mean_reversal import MeanReversal
from util.backtester import perform_mean_reversal_backtest
from trading_rules.position_data import Positions

class TestBacktester(unittest.TestCase):


    def test_backtester_mean_reversal(self):

        market_prices = [{
            "close": 100,
            "timestamp": pd.Timestamp(day=22, month=5, year=2026, hour=10)
        },
        {
            "close": 100,
            "timestamp": pd.Timestamp(day=23, month=5, year=2026, hour=11)
        },
        {
            "close": 80,  # TODO: WE HAVE A BUG HERE
            "timestamp": pd.Timestamp(day=24, month=5, year=2026, hour=12)
        },
        {
            "close": 100,
            "timestamp": pd.Timestamp(day=25, month=5, year=2026, hour=13)
        },
        {
            "close": 100,
            "timestamp": pd.Timestamp(day=26, month=5, year=2026, hour=14)
        },
        {
            "close": 90,
            "timestamp": pd.Timestamp(day=27, month=5, year=2026, hour=10)
        },
        {
            "close": 70,
            "timestamp": pd.Timestamp(day=28, month=5, year=2026, hour=10)
        },
        {
            "close": 80,
            "timestamp": pd.Timestamp(day=29, month=5, year=2026, hour=13)
        },
        {
            "close": 69,
            "timestamp": pd.Timestamp(day=29, month=5, year=2026, hour=15)
        },
        ]

        price_df = pd.DataFrame(market_prices)
        

        price_df.set_index("timestamp", inplace=True)
        mean_reversal_rule = MeanReversal(lookback_window=5)
        market_data = MarketData(price_df)
        positions = Positions(cash=1000)

        positions = perform_mean_reversal_backtest("TEST", mean_reversal_rule, market_data, positions)
        transactions_df = positions.get_transaction_history_df()

        print(transactions_df)

        assert True == False


