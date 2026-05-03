"""Simple Polymarket historical price fetcher."""

from __future__ import annotations

import sys
import os

project_root = os.path.join(os.path.dirname(__file__), '..')
trading_rules_dir = os.path.join(project_root, 'util')
sys.path.insert(0, project_root)
sys.path.insert(0, trading_rules_dir)

import pandas as pd

from util.polymarket_client import PolymarketClient


MARKET_SLUG = "will-jesus-christ-return-before-2027"
OUTCOME = "Yes"
INTERVAL = "all"
FIDELITY_MINUTES = 1


def get_jesus_return_price_history() -> pd.DataFrame:
    """Fetch historical prices for the Yes side of the Jesus return market."""
    client = PolymarketClient()
    prices = client.get_both_outcomes_price_history(
        market_slug=MARKET_SLUG,
        interval=INTERVAL,
        fidelity=FIDELITY_MINUTES,
    )

    print()
    print(prices)

    return prices


if __name__ == "__main__":
    get_jesus_return_price_history()
