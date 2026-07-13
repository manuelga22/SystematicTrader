# trading_rules Code Rules

These rules apply to all code under `trading_rules`. They supplement the root `AGENTS.md` file. 
**Before reading this, you MUST READ THE ROOT LEVEL AGENTS.md file**

## Module Overview

`trading_rules/` is a vectorized backtesting toolkit built on pandas. Entry rules
produce boolean signal Series, exit rules are closures evaluated per bar, and the
engine simulates a single-position, all-in long strategy over OHLCV data with
realistic fills (slippage) and taker fees.

## Files

- **`engine.py`** — This file is the heart of the engine. It has a single backtest() function that returns
  the value of the equity and all the trades through time, while the strategy was running.

- **`entries.py`** — Entry signal generators. Each takes an DataFrame with price information
  (high, low, close, open) and returns a boolean `pd.Series` aligned to it (True = buy on that bar).

- **`exits.py`** — Exit rule factories. Each returns a callable with signature
  `rule(pos, price, data, i) -> bool` that the engine evaluates on every bar while
  holding a position. 

- **`fills.py`** — Order execution pricing. `SlippageParams` holds a fixed
  spread (bps) plus an ATR-proportional volatility component. `OrderFiller`
  converts an order on bar `i` into its executed price — base price (close/open
  per `FillAtEnum`) plus signed slippage so buys fill higher and sells lower —
  and `next_bar_fill()` delays execution to bar `i+1` to avoid lookahead bias.
  `get_slippage_cost()` computes the per-share slippage itself.

- **`fees.py`** — Taker fee models. `FeeParams` selects a `FeeModel` (FREE, BPS,
  or POLYMARKET) with a rate in basis points, an optional minimum fee, and a
  rebate share. 

- **`metrics.py`** — Post-backtest performance analysis. The `Metrics` class
  wraps the engine's `trades` and `equity` outputs and computes per-bar
  simple/log returns, annualized Sharpe ratio (resampled to daily), CAGR, and
  max drawdown; `summary()` returns them all as a one-row DataFrame.

- **`common.py`** — Shared constants and indicators: column-name constants
  (`OPEN`, `HIGH`, `LOW`, `CLOSE`, `VOLUME`, `ATR`) used across the package, and
  `compute_atr(df, period)` which returns an EWMA-smoothed Average True Range.

- **`timeframes.py`** — `TimeframesEnum`: canonical bar-interval strings
  (`1Min` through `1M`) for use with data providers and resampling.

- **`README.md`** — ⚠️ Outdated. Describes a previous OOP design
  (`TradingRule` ABC, `MarketData`, `Positions`, signal enums) that has been
  removed; the current package is the functional engine described above.

- **`AGENTS.MD`** — Code rules for agents working in this package
  (currently a mostly empty skeleton).




