import unittest
import pandas as pd
from trading_rules.position_data import Positions, PositionData
from trading_rules.market_data import MarketData
from util.porfolio_performance import PortfolioPerformance


class TestPortfolioPerformance(unittest.TestCase):
    """Unit tests for the PortfolioPerformance class."""

    def test_parse_daily_returns(self):

        market_data_df = pd.DataFrame([{"timestamp": pd.Timestamp(day=22, month=2, year=2026, hour=12), "symbol": "TEST", "close": 50},
                                       {"timestamp": pd.Timestamp(day=22, month=2, year=2026, hour=13), "symbol": "TEST", "close": 51},
                                       {"timestamp": pd.Timestamp(day=23, month=2, year=2026), "symbol": "TEST", "close": 48},
                                       {"timestamp": pd.Timestamp(day=24, month=2, year=2026), "symbol": "TEST", "close": 52}])
        market_data_df.set_index('timestamp', inplace=True)
        market_data = MarketData(market_data_df)
        positions = Positions(5000)
        positions_stack = [
            PositionData(symbol="TEST", quantity=5, entry_price=1000, action="BUY", 
                         cash_balance=0, timestamp=pd.Timestamp(day=22, month=2, year=2026)),
            PositionData(symbol="TEST", quantity=3, entry_price=1000, action="SELL", 
                         cash_balance=2000, timestamp=pd.Timestamp(day=22, month=2, year=2026)),
        ]
        positions.positions_stack = positions_stack

        expected_return_df = pd.DataFrame([
            {"timestamp": pd.Timestamp(day=22, month=2, year=2026, hour=12), "cash_balance": 2000, "portfolio_value": 100.0, "daily_return": (100 - 5000) / 5000},
            {"timestamp": pd.Timestamp(day=22, month=2, year=2026, hour=13), "cash_balance": 2000, "portfolio_value": 102.0, "daily_return": (102 - 100) / 100},
            {"timestamp": pd.Timestamp(day=23, month=2, year=2026),"cash_balance": 2000, "portfolio_value": 96.0,  "daily_return": (96 - 102) / 102},
            {"timestamp": pd.Timestamp(day=23, month=2, year=2026),"cash_balance": 2000, "portfolio_value": 96.0,  "daily_return": (96 - 102) / 102},
        ]).set_index("timestamp")
        print(expected_return_df)

        pp = PortfolioPerformance(positions, 5000, market_data)
        returns_df = pp.get_daily_returns_history(start_ts=pd.Timestamp(day=22, month=2, year=2026), 
                                                  end_ts=pd.Timestamp(day=24, month=2, year=2026))
        
        print(returns_df)
        self.assertEqual(expected_return_df, returns_df)



if __name__ == "__main__":
    unittest.main()
