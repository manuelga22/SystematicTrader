Trading Rules Module
=====================

Overview
--------

The `trading_rules` package implements a small, object-oriented framework for rule-based trading decision logic. Each rule is encapsulated as a class that inspects market and position state and returns a concise signal indicating whether to BUY, HOLD, SELL, or return NONE.

Design Principles
-----------------

- Object-oriented: Rules are classes that inherit a common base (`TradingRule`).
- Minimal surface area: Rules accept only the data they need (`MarketData`, `Positions`) and return a `TradingSignalEnum` value. They do not execute orders.
- Deterministic and side-effect free: `generate_signal` implementations should only read inputs and return a decision.
- Composable: an external strategy orchestrator can instantiate multiple rules and aggregate their outputs.

Core Components
---------------

- `TradingRule` (abstract base): defines the contract `generate_signal(self, market_data, positions_data) -> TradingSignalEnum`.
- `MarketData`: convenience wrapper around a price series (Pandas DataFrame) exposing helpers such as `get_latest_price()` and `get_mean(window)`.
- `Positions` / `PositionData`: simple position storage objects exposing methods like `are_we_holding_positions()` and `get_entry_price()`.
- `signals`: contains `TradingSignalEnum` (BUY, HOLD, SELL, NONE) and `TradingSignal` wrapper for richer metadata.

Example Rules
-------------

- `EarlyProfitTaker`: exits when unrealized profit for the active position exceeds a configured threshold.
- `EarlyLossTaker`: exits when unrealized loss exceeds a configured threshold.
- `MeanReversal`: signals BUY when a short-window mean falls below a long-window mean (simple mean-reversion heuristic).

Implementation Notes
--------------------

- Rules use package-relative imports and Python's `logging` module for diagnostics.
- The current implementation assumes at most one active position for the sample rules. To support multiple concurrent positions, rules should iterate over the `Positions.positions` list or the project should define clearer single-vs-multi-position semantics.
- `TradingRule` is implemented as an abstract base class (`abc.ABC`) to ensure concrete rules implement `generate_signal`.

Extensibility
-------------

To add a new rule:

1. Create a new module under `trading_rules/`.
2. Subclass `TradingRule` and implement `generate_signal(self, market_data, positions_data)`.
3. Keep logic deterministic and side-effect free; use `logging` for telemetry.

Testing
-------

Rules are easy to unit test by providing synthetic `MarketData` (a small DataFrame) and a `Positions` instance with crafted `PositionData`. Test edge cases such as threshold equality, empty datasets, and NaN values in price series.

