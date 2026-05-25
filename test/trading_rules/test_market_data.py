import unittest
import pandas as pd
from trading_rules.market_data import MarketData


class TestMarketData(unittest.TestCase):

    def test_get_price_at_time_exact_match(self):
        df = pd.DataFrame([
            {"timestamp": pd.Timestamp("2024-01-01 09:00"), "symbol": "AAPL", "close": 150.0},
            {"timestamp": pd.Timestamp("2024-01-01 10:00"), "symbol": "AAPL", "close": 155.0},
            {"timestamp": pd.Timestamp("2024-01-01 11:00"), "symbol": "AAPL", "close": 160.0},
        ]).set_index("timestamp")

        md = MarketData(df)
        price = md.get_price_at_time("AAPL", pd.Timestamp("2024-01-01 10:00"))
        self.assertEqual(price, 155.0)

    def test_get_price_at_time_between_entries_returns_last_known(self):
        df = pd.DataFrame([
            {"timestamp": pd.Timestamp("2024-01-01 09:00"), "symbol": "AAPL", "close": 150.0},
            {"timestamp": pd.Timestamp("2024-01-01 10:00"), "symbol": "AAPL", "close": 155.0},
            {"timestamp": pd.Timestamp("2024-01-01 11:00"), "symbol": "AAPL", "close": 160.0},
        ]).set_index("timestamp")

        md = MarketData(df)
        price = md.get_price_at_time("AAPL", pd.Timestamp("2024-01-01 10:30"))
        self.assertEqual(price, 155.0)

    def test_get_price_at_time_different_symbols_isolated(self):
        df = pd.DataFrame([
            {"timestamp": pd.Timestamp("2024-01-01 09:00"), "symbol": "AAPL", "close": 150.0},
            {"timestamp": pd.Timestamp("2024-01-01 09:00"), "symbol": "GOOG", "close": 2800.0},
            {"timestamp": pd.Timestamp("2024-01-01 10:00"), "symbol": "AAPL", "close": 155.0},
        ]).set_index("timestamp")

        md = MarketData(df)
        self.assertEqual(md.get_price_at_time("AAPL", pd.Timestamp("2024-01-01 10:00")), 155.0)
        self.assertEqual(md.get_price_at_time("GOOG", pd.Timestamp("2024-01-01 10:00")), 2800.0)


if __name__ == "__main__":
    unittest.main()
