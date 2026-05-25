import unittest
import pandas as pd
from trading_rules.position_data import Positions


class TestPositions(unittest.TestCase):
    """Unit tests for the Positions class."""

    def setUp(self):
        """Set up test fixtures."""
        self.positions = Positions(cash=10000.0)

    def test_buy_sell(self):
        
        self.positions.buy_position(symbol="TEST", 
                                    quantity=2, 
                                    entry_price=10,
                                    timestamp=pd.Timestamp(year=2026,
                                                           month=5,
                                                           day=22))
        self.assertEqual(len(self.positions.positions_stack), 1)
        self.assertEqual(self.positions.get_available_cash(), 9980.0)
        self.assertEqual(self.positions.stock_quantity_dict.get("TEST"), 2)
        self.assertEqual(self.positions.are_we_holding_positions(), True)

        self.positions.sell_position(symbol="TEST",
                                     quantity=1,
                                     current_price=10,
                                     timestamp=pd.Timestamp(year=2025,
                                                            month=5,
                                                            day=21))
        self.assertEqual(len(self.positions.positions_stack), 2)
        self.assertEqual(self.positions.get_available_cash(), 9990.0)
        self.assertEqual(self.positions.stock_quantity_dict.get("TEST"), 1)
        self.assertEqual(self.positions.are_we_holding_positions(), True)

        self.positions.sell_position(symbol="TEST",
                                     quantity=1,
                                     current_price=10,
                                     timestamp=pd.Timestamp(year=2025,
                                                            month=5,
                                                            day=21))
        self.assertEqual(len(self.positions.positions_stack), 3)
        self.assertEqual(self.positions.get_available_cash(), 10000.0)
        self.assertEqual(self.positions.stock_quantity_dict.get("TEST"), 0)
        self.assertEqual(self.positions.are_we_holding_positions(), False)

    def test_holding_time(self):
        self.positions.buy_position(symbol="TEST", 
                            quantity=2, 
                            entry_price=10,
                            timestamp=pd.Timestamp(year=2025,
                                                   month=5,
                                                   day=21))
        self.positions.sell_position(symbol="TEST",
                             quantity=1,
                             current_price=10,
                             timestamp=pd.Timestamp(year=2025,
                                                    month=5,
                                                    day=25))
        current_timestamp = pd.Timestamp(day=22, month=5, year=2025)
        holding_period_minutes = self.positions.get_holding_time_minutes("TEST", 
                                                                         current_timestamp)
        self.assertEqual(holding_period_minutes, 1440)

    def test_get_holdings_at_time(self):
        self.positions.buy_position(symbol="AAPL", quantity=5, entry_price=100,
                                    timestamp=pd.Timestamp("2024-01-01 09:00"))
        self.positions.buy_position(symbol="GOOG", quantity=2, entry_price=200,
                                    timestamp=pd.Timestamp("2024-01-01 10:00"))
        self.positions.sell_position(symbol="AAPL", quantity=3, current_price=110,
                                     timestamp=pd.Timestamp("2024-01-01 11:00"))

        # before any transactions
        self.assertEqual(self.positions.get_holdings_at_time(pd.Timestamp("2024-01-01 08:00")), {})

        # after first buy only
        self.assertEqual(self.positions.get_holdings_at_time(pd.Timestamp("2024-01-01 09:00")), {"AAPL": 5})

        # after both buys
        self.assertEqual(self.positions.get_holdings_at_time(pd.Timestamp("2024-01-01 10:00")), {"AAPL": 5, "GOOG": 2})

        # after the sell — AAPL should be reduced by 3
        self.assertEqual(self.positions.get_holdings_at_time(pd.Timestamp("2024-01-01 11:00")), {"AAPL": 2, "GOOG": 2})


if __name__ == "__main__":
    unittest.main()
