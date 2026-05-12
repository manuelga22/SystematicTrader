import unittest
import pandas as pd
from trading_rules.position_data import Positions, PositionData, BUY

class TestPositionData(unittest.TestCase):
    """Unit tests for the PositionData class."""

    def test_position_data_initialization(self):
        """Test PositionData initialization."""
        pos = PositionData(
            symbol="AAPL",
            quantity=10,
            entry_price=150.0,
            action=BUY,
            timestamp="2025-01-01"
        )
        self.assertEqual(pos.symbol, "AAPL")
        self.assertEqual(pos.quantity, 10)
        self.assertEqual(pos.entry_price, 150.0)
        self.assertEqual(pos.action, BUY)
        self.assertEqual(pos.timestamp, "2025-01-01")

    def test_get_entry_price(self):
        """Test get_entry_price method."""
        pos = PositionData("TSLA", 5, 200.0, BUY)
        self.assertEqual(pos.get_entry_price(), 200.0)


class TestPositions(unittest.TestCase):
    """Unit tests for the Positions class."""

    def setUp(self):
        """Set up test fixtures."""
        self.positions = Positions(cash=10000.0)

    def test_positions_initialization(self):
        """Test Positions initialization."""
        pos = Positions(cash=5000.0)
        self.assertEqual(pos.cash, 5000.0)
        self.assertEqual(len(pos.positions), 0)
        self.assertEqual(len(pos.trade_history), 0)

    def test_get_available_cash(self):
        """Test get_available_cash method."""
        self.assertEqual(self.positions.get_available_cash(), 10000.0)

    def test_are_we_holding_positions_empty(self):
        """Test are_we_holding_positions when no positions are held."""
        self.assertFalse(self.positions.are_we_holding_positions())

    def test_add_position_success(self):
        """Test adding a position successfully."""
        initial_cash = self.positions.get_available_cash()
        self.positions.add_position("AAPL", 10, 150.0)
        
        self.assertEqual(len(self.positions.positions), 1)
        self.assertEqual(len(self.positions.trade_history), 1)
        self.assertEqual(self.positions.get_available_cash(), initial_cash - 1500.0)
        self.assertTrue(self.positions.are_we_holding_positions())

    def test_add_position_insufficient_cash(self):
        """Test adding a position with insufficient cash."""
        self.positions.add_position("AAPL", 100, 150.0)  # Would cost 15,000, but only have 10,000
        
        self.assertEqual(len(self.positions.positions), 0)
        self.assertEqual(self.positions.get_available_cash(), 10000.0)

    def test_add_multiple_positions(self):
        """Test adding multiple positions."""
        self.positions.add_position("AAPL", 10, 100.0)  # Costs 1,000
        self.positions.add_position("GOOGL", 5, 1000.0)  # Costs 5,000
        
        self.assertEqual(len(self.positions.positions), 2)
        self.assertEqual(len(self.positions.trade_history), 2)
        self.assertEqual(self.positions.get_available_cash(), 4000.0)

    def test_remove_position_success(self):
        """Test removing a position successfully."""
        self.positions.add_position("AAPL", 10, 150.0)
        cash_after_buy = self.positions.get_available_cash()
        
        removed_pos = self.positions.remove_position("AAPL", 160.0)
        
        self.assertIsNotNone(removed_pos)
        self.assertEqual(removed_pos.symbol, "AAPL")
        self.assertEqual(removed_pos.quantity, 10)
        self.assertEqual(len(self.positions.positions), 0)
        self.assertEqual(len(self.positions.trade_history), 2)  # Buy + Sell
        self.assertFalse(self.positions.are_we_holding_positions())

    def test_remove_position_not_found(self):
        """Test removing a position that doesn't exist."""
        self.positions.add_position("AAPL", 10, 150.0)
        
        removed_pos = self.positions.remove_position("GOOGL", 200.0)
        
        self.assertIsNone(removed_pos)
        self.assertEqual(len(self.positions.positions), 1)

    def test_parse_positions_single_trade(self):
        """Test parse_positions with a single completed trade."""
        self.positions.add_position("AAPL", 10, 150.0)
        self.positions.remove_position("AAPL", 160.0)
        
        df = self.positions.parse_positions()
        
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["symbol"], "AAPL")
        self.assertEqual(df.iloc[0]["quantity"], 10)
        self.assertEqual(df.iloc[0]["entry_price"], 150.0)
        self.assertEqual(df.iloc[0]["sold_price"], 160.0)

    def test_parse_positions_multiple_trades(self):
        """Test parse_positions with multiple completed trades."""
        self.positions.add_position("AAPL", 10, 150.0)
        self.positions.remove_position("AAPL", 160.0)
        self.positions.add_position("GOOGL", 5, 1000.0)
        self.positions.remove_position("GOOGL", 1100.0)
        
        df = self.positions.parse_positions()
        
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["symbol"], "AAPL")
        self.assertEqual(df.iloc[1]["symbol"], "GOOGL")

    def test_get_returns_from_trade_history(self):
        """Test get_returns_from_trade_history calculation."""
        self.positions.add_position("AAPL", 10, 100.0)
        self.positions.remove_position("AAPL", 110.0)
        
        returns_df = self.positions.get_returns_from_trade_history()
        
        self.assertEqual(len(returns_df), 1)
        self.assertAlmostEqual(returns_df.iloc[0]["returns"], 0.1)  # 10% return

    def test_get_returns_from_trade_history_loss(self):
        """Test get_returns_from_trade_history with a losing trade."""
        self.positions.add_position("TSLA", 5, 200.0)
        self.positions.remove_position("TSLA", 180.0)
        
        returns_df = self.positions.get_returns_from_trade_history()
        
        self.assertEqual(len(returns_df), 1)
        self.assertAlmostEqual(returns_df.iloc[0]["returns"], -0.1)  # -10% return

    def test_show_positions_with_positions(self):
        """Test show_positions when holding positions."""
        self.positions.add_position("AAPL", 10, 150.0)
        self.positions.add_position("GOOGL", 5, 1000.0)
        
        positions_list = self.positions.show_positions()
        
        self.assertEqual(len(positions_list), 2)
        self.assertEqual(positions_list[0].symbol, "AAPL")
        self.assertEqual(positions_list[1].symbol, "GOOGL")

    def test_show_positions_empty(self):
        """Test show_positions when no positions are held."""
        positions_list = self.positions.show_positions()
        
        self.assertEqual(len(positions_list), 0)

    def test_get_holding_time_minutes(self):
        """Test get_holding_time_minutes."""
        # Create timestamp in milliseconds
        entry_time_ms = pd.Timestamp("2025-01-01 10:00:00")
        self.positions.add_position("AAPL", 10, 150.0, timestmap=entry_time_ms)
        
        # Create current time 30 minutes later
        current_time = pd.Timestamp("2025-01-01 10:30:00")
        
        holding_time = self.positions.get_holding_time_minutes(current_time)
        
        self.assertAlmostEqual(holding_time, 30, delta=1)  # Allow 1 minute tolerance for timing

    def test_cash_management_across_trades(self):
        """Test cash management across multiple trades."""
        initial_cash = 10000.0
        
        # First trade: buy 10 AAPL at $100
        self.positions.add_position("AAPL", 10, 100.0)
        self.assertEqual(self.positions.get_available_cash(), initial_cash - 1000.0)
        
        # Close first trade at $110
        self.positions.remove_position("AAPL", 110.0)
        # Cash should still be 9000 (it doesn't get updated when selling)
        self.assertEqual(self.positions.get_available_cash(), initial_cash - 1000.0)
        
        # Second trade: buy 5 GOOGL at $1000
        self.positions.add_position("GOOGL", 5, 1000.0)
        self.assertEqual(self.positions.get_available_cash(), initial_cash - 1000.0 - 5000.0)


if __name__ == "__main__":
    unittest.main()
