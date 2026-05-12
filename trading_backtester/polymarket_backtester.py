"""Simple Polymarket historical price fetcher."""

from __future__ import annotations

import sys
import os

project_root = os.path.join(os.path.dirname(__file__), '..')
trading_rules_dir = os.path.join(project_root, 'util')
sys.path.insert(0, project_root)
sys.path.insert(0, trading_rules_dir)

import pandas as pd
from util.polymarket_client import PolymarketAPIClient
from trading_rules.position_data import Positions
from trading_rules.market_data import MarketData
from util.backtester import perform_mean_reversal_backtest


MARKET_SLUG = "will-jesus-christ-return-in-2025"
FIDELITY_MINUTES = 1



if __name__ == "__main__":

    client = PolymarketAPIClient()

    market = client.get_price_history_by_outcome(MARKET_SLUG, desired_outcome="No")

    market_data = MarketData(market)
    positions = Positions(cash=1000.0)

    positions = perform_mean_reversal_backtest(market_data, positions)

    positions_df = positions.get_returns_from_trade_history()

    print(positions_df)



