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
from util.data_processor import parse_timestamp
from trading_rules.position_data import Positions
from trading_rules.mean_reversal import MeanReversal
from trading_rules.market_data import MarketData
from util.backtester import perform_mean_reversal_backtest


MARKET_SLUG = "will-jesus-christ-return-in-2025"
FIDELITY_MINUTES = 1


def get_jesus_return_price_history(market_slug: str = MARKET_SLUG, interval: str = "all") -> pd.DataFrame:
    """Fetch historical prices for the Yes side of the Jesus return market."""
    client = PolymarketAPIClient()
    prices = client.get_both_outcomes_price_history(
        market_slug=market_slug,
        interval=interval,
        fidelity=FIDELITY_MINUTES,
    )

    return prices[0]


if __name__ == "__main__":

    price_data = get_jesus_return_price_history()

    price_data = parse_timestamp(price_data)

    print(price_data['price'])
    
    market_data = MarketData(price_data)
    positions = Positions(cash=1000.0)
    mean_reversal_rule = MeanReversal()


    positions = perform_mean_reversal_backtest(mean_reversal_rule, market_data, positions)

    print(len(positions.trade_history))



