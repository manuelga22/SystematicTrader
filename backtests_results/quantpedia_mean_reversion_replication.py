"""Replication of Quantpedia's "Exploiting Mean Reversion in Decentralized
Prediction Markets" study on Polymarket binary contracts.

Article:
    https://quantpedia.com/exploiting-mean-reversion-in-decentralized-prediction-markets-evidence-from-polymarket-binary-contracts/

Strategy (as described in the article)
--------------------------------------
* Data: a single binary contract sampled on a 10-minute grid over ~1 year.
* Entry: go LONG when the current price is at or below its X-day rolling
  minimum (the contract looks "undervalued" relative to its recent range).
* Exit: hold the position for exactly Y days, then close it. The full capital
  is reinvested on every entry and there are no overlapping positions.
* The study sweeps a 12-variant grid: X (lookback) in {5, 10, 20} days and
  Y (holding period) in {1, 2, 3, 5} days.
* Two friction scenarios are evaluated: a frictionless (zero-spread) book and
  a 10 bps per-trade cost (combined fees + slippage).

Reported metrics per variant: CAR (CAGR), annualised volatility, Sharpe,
maximum drawdown and Calmar (CAR / |MaxDD|).

This implementation uses the ``vectorbt`` library for the backtest itself
(``vbt.Portfolio.from_signals``), matching the pattern already used in the
project's notebooks. It reuses the project's data client
(``PolymarketAPIClient`` / ``MarketData``) to load prices.
"""

from __future__ import annotations

import itertools
import os
import sys

# Make the project root importable when run as a plain script from anywhere.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
import vectorbt as vbt

from util.polymarket_client import PolymarketAPIClient
from util.data_processor import TickDataIntervalEnum
from trading_rules.market_data import MarketData, PRICE


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# The three contracts studied in the article. Slugs match Polymarket URLs.
# Add the China/Alien slugs here to reproduce the full study.
CONTRACTS = {
    "jesus": "will-jesus-christ-return-in-2025",
    # "china": "<china-contract-slug>",
    # "alien": "<alien-contract-slug>",
}

DESIRED_OUTCOME = "No"          # the article works the "No" leg of each binary
RESAMPLE_RULE = "10min"         # 10-minute grid, as in the paper
INITIAL_CASH = 10_000.0

# Paper's parameter grid.
LOOKBACK_DAYS_GRID = [5, 10, 20]      # X
HOLDING_DAYS_GRID = [1, 2, 3, 5]      # Y

# Friction scenarios, expressed as a per-trade fee fraction passed to vectorbt.
FRICTION_SCENARIOS = {
    "zero_spread": 0.0,
    "10_bps": 0.0010,
}

# 10-minute bars in one day, used to convert day-based parameters into bar counts.
BARS_PER_DAY = 24 * 6  # 144

# vectorbt annualises using this many periods per year (daily returns -> 252).
vbt.settings.array_wrapper["freq"] = RESAMPLE_RULE
vbt.settings.returns["year_freq"] = "252 days"


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def load_contract(market_slug: str) -> pd.Series:
    """Load a contract's "No"-leg price history on a 10-minute grid.

    Mirrors the snippet provided for this task: pull the 5-minute history, wrap
    it in ``MarketData``, resample to 10 minutes and forward-fill gaps. Returns a
    clean close-price Series ready for vectorbt.
    """
    client = PolymarketAPIClient()
    market = client.get_price_history_by_outcome(
        market_slug,
        desired_outcome=DESIRED_OUTCOME,
        interval=TickDataIntervalEnum.FIVE_MINUTES,
    )
    market["symbol"] = market_slug

    market_data = MarketData(market)
    resampled = market_data.df.resample(RESAMPLE_RULE).last()
    market_data.df = resampled

    price = resampled[PRICE].astype(float).ffill().dropna()
    price.name = "close"
    return price


# --------------------------------------------------------------------------- #
# Backtest core (vectorbt)
# --------------------------------------------------------------------------- #

def build_signals(price: pd.Series, lookback_days: int, holding_days: int) -> tuple[pd.Series, pd.Series]:
    """Build entry/exit boolean signals for the rolling-minimum rule.

    Entry: price <= trailing X-day rolling minimum. The rolling window is shifted
    one bar so the test only uses information available before the current bar.
    Exit: exactly Y days (Y * bars-per-day) after the corresponding entry bar.
    vectorbt collapses overlapping entries, so reinvestment is one-position-at-a-time.
    """
    window = lookback_days * BARS_PER_DAY
    hold = holding_days * BARS_PER_DAY

    rolling_min = price.shift(1).rolling(window=window, min_periods=window).min()
    entries = ((price <= rolling_min) & (price > 0)).fillna(False).astype(bool)
    # Exit exactly `hold` bars after each entry. Shift on a bool Series keeps the
    # dtype clean (no object downcast) once the NaNs introduced by the shift are
    # replaced with False.
    exits = entries.shift(hold)
    exits = exits.where(exits.notna(), False).astype(bool)

    return entries, exits


def run_variant(price: pd.Series, lookback_days: int, holding_days: int, fees: float) -> vbt.Portfolio:
    """Run a single (X, Y, fees) variant through vectorbt and return the Portfolio."""
    entries, exits = build_signals(price, lookback_days, holding_days)
    return vbt.Portfolio.from_signals(
        close=price,
        entries=entries,
        exits=exits,
        fees=fees,
        freq=RESAMPLE_RULE,
        init_cash=INITIAL_CASH,
    )


# --------------------------------------------------------------------------- #
# Performance metrics (read off vectorbt, computed on daily returns)
# --------------------------------------------------------------------------- #

def extract_metrics(pf: vbt.Portfolio) -> dict[str, float]:
    """Pull the article's metrics out of a vectorbt Portfolio.

    CAR (CAGR), annualised volatility and Sharpe are computed by vectorbt from
    daily-resampled returns; Calmar is CAR / |MaxDD|.
    """
    # Resample the portfolio value to daily so Sharpe/vol use daily returns
    # (annualised with 252) regardless of the 10-minute bar frequency.
    daily_returns = pf.value().resample("1D").last().dropna().pct_change().dropna()

    car = pf.annualized_return()
    ann_vol = pf.annualized_volatility()
    sharpe = pf.sharpe_ratio()
    max_dd = pf.max_drawdown()  # negative fraction
    calmar = car / abs(max_dd) if max_dd and not np.isnan(max_dd) and max_dd != 0 else np.nan

    return {
        "CAR": car,
        "AnnVol": ann_vol,
        "Sharpe": sharpe,
        "MaxDD": max_dd,
        "Calmar": calmar,
        "n_trades": int(pf.trades.count()),
    }


# --------------------------------------------------------------------------- #
# Grid sweep / orchestration
# --------------------------------------------------------------------------- #

def sweep_contract(name: str, price: pd.Series) -> pd.DataFrame:
    """Run the full X x Y x friction grid for one contract and tabulate metrics."""
    rows = []
    for friction_name, fees in FRICTION_SCENARIOS.items():
        for x, y in itertools.product(LOOKBACK_DAYS_GRID, HOLDING_DAYS_GRID):
            pf = run_variant(price, lookback_days=x, holding_days=y, fees=fees)
            metrics = extract_metrics(pf)
            rows.append({
                "contract": name,
                "friction": friction_name,
                "X_lookback_days": x,
                "Y_holding_days": y,
                "n_trades": metrics.pop("n_trades"),
                **metrics,
            })
    return pd.DataFrame(rows)


def format_table(df: pd.DataFrame) -> str:
    """Pretty-print the results grid with percentages where it helps."""
    pretty = df.copy()
    for col in ("CAR", "AnnVol", "MaxDD"):
        pretty[col] = (pretty[col] * 100).map(lambda v: f"{v:6.2f}%" if pd.notna(v) else "  n/a")
    for col in ("Sharpe", "Calmar"):
        pretty[col] = pretty[col].map(lambda v: f"{v:6.2f}" if pd.notna(v) else "  n/a")
    return pretty.to_string(index=False)


def main() -> None:
    all_results = []
    for name, slug in CONTRACTS.items():
        print(f"\nLoading contract '{name}' ({slug}) ...")
        price = load_contract(slug)
        span_days = (price.index[-1] - price.index[0]).days
        print(f"  {len(price)} bars on a {RESAMPLE_RULE} grid, spanning ~{span_days} days "
              f"({span_days / 365.25:.2f} years)")

        all_results.append(sweep_contract(name, price))

    if not all_results:
        print("No contracts configured. Add slugs to CONTRACTS.")
        return

    results = pd.concat(all_results, ignore_index=True)

    print("\n" + "=" * 80)
    print("Mean-reversion grid results (vectorbt; Quantpedia replication)")
    print("=" * 80)
    for friction_name in FRICTION_SCENARIOS:
        subset = results[results["friction"] == friction_name]
        print(f"\n--- Friction scenario: {friction_name} ---")
        print(format_table(subset))

    # Highlight the best Sharpe variant under each friction scenario, mirroring
    # the article's focus on how the optimum shifts once costs are introduced.
    print("\n" + "=" * 80)
    print("Best Sharpe per contract & friction scenario")
    print("=" * 80)
    best = (
        results.sort_values("Sharpe", ascending=False)
        .groupby(["contract", "friction"], as_index=False)
        .first()
    )
    print(format_table(best.sort_values(["contract", "friction"])))


if __name__ == "__main__":
    main()
