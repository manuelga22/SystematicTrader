"""Historical backtesting for Polymarket outcome tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from trading_rules.market_data import MarketData
    from trading_rules.position_data import PositionData, Positions
    from trading_rules.signals import TradingSignalEnum
    from trading_rules.trading_rule import TradingRule
except ImportError:  # pragma: no cover - supports direct script execution
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from trading_rules.market_data import MarketData
    from trading_rules.position_data import PositionData, Positions
    from trading_rules.signals import TradingSignalEnum
    from trading_rules.trading_rule import TradingRule

from util.polymarket_client import (
    PolymarketClient,
    PolymarketMarket,
    PolymarketToken,
)


TRADING_DAYS_PER_YEAR = 365.0
SECONDS_PER_YEAR = TRADING_DAYS_PER_YEAR * 24 * 60 * 60


@dataclass(frozen=True)
class PolymarketBacktestConfig:
    """Configuration for one Polymarket outcome-token backtest."""

    market_slug: str | None = None
    token_id: str | None = None
    outcome: str = "Yes"
    start: datetime | str | int | float | None = None
    end: datetime | str | int | float | None = None
    interval: str | None = None
    fidelity: int | None = 1
    initial_capital: float = 1000.0
    position_size: float | None = None
    enter_on_first_tick: bool = True
    close_at_end: bool = True


@dataclass(frozen=True)
class PolymarketTrade:
    timestamp: str
    decision: str
    price: float
    quantity: float
    cash_after: float
    portfolio_value: float
    rule_triggered: str
    pnl: float | None = None


@dataclass(frozen=True)
class PolymarketBacktestMetrics:
    total_pnl: float
    cumulative_return: float
    annualized_return: float
    sharpe_ratio: float
    annualized_average_volatility: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass(frozen=True)
class PolymarketBacktestResult:
    config: PolymarketBacktestConfig
    metrics: PolymarketBacktestMetrics
    trades: list[PolymarketTrade]
    portfolio_history: pd.DataFrame
    price_history: pd.DataFrame
    market: PolymarketMarket | None = None
    token: PolymarketToken | None = None
    warnings: list[str] = field(default_factory=list)


class PolymarketBacktester:
    """Run historical Polymarket token prices through trading rules."""

    def __init__(self, client: PolymarketClient | None = None) -> None:
        self.client = client or PolymarketClient()

    def fetch_price_history(self, config: PolymarketBacktestConfig) -> tuple[
        PolymarketMarket | None,
        PolymarketToken | None,
        pd.DataFrame,
    ]:
        """Fetch price data specified by slug/outcome or token id."""
        if config.market_slug:
            return self.client.get_outcome_price_history(
                market_slug=config.market_slug,
                outcome=config.outcome,
                start=config.start,
                end=config.end,
                interval=config.interval,
                fidelity=config.fidelity,
            )

        if config.token_id:
            return (
                None,
                PolymarketToken(token_id=config.token_id, outcome=config.outcome),
                self.client.get_price_history(
                    token_id=config.token_id,
                    start=config.start,
                    end=config.end,
                    interval=config.interval,
                    fidelity=config.fidelity,
                ),
            )

        raise ValueError("Provide either market_slug or token_id")

    def run(
        self,
        config: PolymarketBacktestConfig,
        rules: TradingRule | Iterable[TradingRule],
        price_history: pd.DataFrame | None = None,
    ) -> PolymarketBacktestResult:
        """Run a backtest and return trades, portfolio history, and metrics."""
        normalized_rules = self._normalize_rules(rules)
        market: PolymarketMarket | None = None
        token: PolymarketToken | None = None

        if price_history is None:
            market, token, price_history = self.fetch_price_history(config)
        else:
            price_history = self._normalize_price_history(price_history, config.token_id)

        if price_history.empty:
            empty_portfolio = pd.DataFrame(columns=["timestamp", "portfolio_value", "cash", "quantity", "price"])
            return PolymarketBacktestResult(
                config=config,
                metrics=self._calculate_metrics(empty_portfolio, [], config.initial_capital),
                trades=[],
                portfolio_history=empty_portfolio,
                price_history=price_history,
                market=market,
                token=token,
                warnings=["No historical prices were returned for the requested market."],
            )

        return self._simulate(config, normalized_rules, price_history, market, token)

    def _simulate(
        self,
        config: PolymarketBacktestConfig,
        rules: list[TradingRule],
        price_history: pd.DataFrame,
        market: PolymarketMarket | None,
        token: PolymarketToken | None,
    ) -> PolymarketBacktestResult:
        cash = float(config.initial_capital)
        quantity = 0.0
        entry_price: float | None = None
        entry_timestamp: str | None = None
        trades: list[PolymarketTrade] = []
        snapshots: list[dict[str, float | str]] = []
        warnings: list[str] = []
        symbol = token.token_id if token else config.token_id or config.market_slug or "POLYMARKET"

        for index in range(len(price_history)):
            current = price_history.iloc[index]
            timestamp = str(current["timestamp"])
            price = float(current["price"])

            lookback_df = price_history.iloc[: index + 1][["timestamp", "price"]].copy()
            market_data = MarketData(lookback_df)
            positions_data = Positions(cash=cash)
            if quantity > 0 and entry_price is not None:
                positions_data.positions.append(
                    PositionData(
                        symbol=symbol,
                        quantity=quantity,
                        entry_price=entry_price,
                        timestamp=entry_timestamp,
                    )
                )

            signal, rule_name = self._first_signal(rules, market_data, positions_data)

            if quantity <= 0 and (signal == TradingSignalEnum.BUY or (config.enter_on_first_tick and index == 0)):
                dollars_to_invest = min(cash, config.position_size or cash)
                if price <= 0:
                    warnings.append(f"Skipped BUY at {timestamp}; price was not positive.")
                elif dollars_to_invest > 0:
                    quantity = dollars_to_invest / price
                    cash -= dollars_to_invest
                    entry_price = price
                    entry_timestamp = timestamp
                    portfolio_value = cash + quantity * price
                    trades.append(
                        PolymarketTrade(
                            timestamp=timestamp,
                            decision="BUY",
                            price=price,
                            quantity=quantity,
                            cash_after=cash,
                            portfolio_value=portfolio_value,
                            rule_triggered=rule_name if signal == TradingSignalEnum.BUY else "Initial entry",
                        )
                    )

            elif quantity > 0 and signal == TradingSignalEnum.SELL:
                proceeds = quantity * price
                realized_pnl = quantity * (price - (entry_price or price))
                cash += proceeds
                portfolio_value = cash
                trades.append(
                    PolymarketTrade(
                        timestamp=timestamp,
                        decision="SELL",
                        price=price,
                        quantity=quantity,
                        cash_after=cash,
                        portfolio_value=portfolio_value,
                        rule_triggered=rule_name,
                        pnl=realized_pnl,
                    )
                )
                quantity = 0.0
                entry_price = None
                entry_timestamp = None

            snapshots.append(
                {
                    "timestamp": timestamp,
                    "portfolio_value": cash + quantity * price,
                    "cash": cash,
                    "quantity": quantity,
                    "price": price,
                }
            )

        if config.close_at_end and quantity > 0:
            final = price_history.iloc[-1]
            final_timestamp = str(final["timestamp"])
            final_price = float(final["price"])
            proceeds = quantity * final_price
            realized_pnl = quantity * (final_price - (entry_price or final_price))
            cash += proceeds
            trades.append(
                PolymarketTrade(
                    timestamp=final_timestamp,
                    decision="SELL",
                    price=final_price,
                    quantity=quantity,
                    cash_after=cash,
                    portfolio_value=cash,
                    rule_triggered="End of backtest",
                    pnl=realized_pnl,
                )
            )
            snapshots[-1]["portfolio_value"] = cash
            snapshots[-1]["cash"] = cash
            snapshots[-1]["quantity"] = 0.0

        portfolio_history = pd.DataFrame(snapshots)
        metrics = self._calculate_metrics(portfolio_history, trades, config.initial_capital)

        return PolymarketBacktestResult(
            config=config,
            metrics=metrics,
            trades=trades,
            portfolio_history=portfolio_history,
            price_history=price_history,
            market=market,
            token=token,
            warnings=warnings,
        )

    @staticmethod
    def _first_signal(
        rules: list[TradingRule],
        market_data: MarketData,
        positions_data: Positions,
    ) -> tuple[TradingSignalEnum, str]:
        for rule in rules:
            signal = rule.generate_signal(market_data, positions_data)
            if signal in (TradingSignalEnum.BUY, TradingSignalEnum.SELL):
                return signal, rule.__class__.__name__
        return TradingSignalEnum.NONE, ""

    @staticmethod
    def _normalize_rules(rules: TradingRule | Iterable[TradingRule]) -> list[TradingRule]:
        if isinstance(rules, TradingRule):
            return [rules]
        normalized = list(rules)
        if not normalized:
            raise ValueError("At least one trading rule is required")
        return normalized

    @staticmethod
    def _normalize_price_history(df: pd.DataFrame, token_id: str | None = None) -> pd.DataFrame:
        required_columns = {"timestamp", "price"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"price_history missing columns: {missing_columns}")

        normalized = df.copy()
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], utc=True)
        normalized["price"] = pd.to_numeric(normalized["price"], errors="coerce")
        if "token_id" not in normalized.columns:
            normalized["token_id"] = token_id
        normalized = normalized.dropna(subset=["timestamp", "price"])
        normalized = normalized.sort_values("timestamp").drop_duplicates("timestamp")
        return normalized.reset_index(drop=True)

    @staticmethod
    def _calculate_metrics(
        portfolio_history: pd.DataFrame,
        trades: list[PolymarketTrade],
        initial_capital: float,
    ) -> PolymarketBacktestMetrics:
        if portfolio_history.empty or initial_capital <= 0:
            return PolymarketBacktestMetrics(
                total_pnl=0.0,
                cumulative_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                annualized_average_volatility=0.0,
                max_drawdown=0.0,
                total_trades=len(trades),
                winning_trades=0,
                losing_trades=0,
            )

        values = pd.to_numeric(portfolio_history["portfolio_value"], errors="coerce").dropna()
        final_value = float(values.iloc[-1])
        cumulative_return = final_value / initial_capital - 1.0
        total_pnl = final_value - initial_capital
        period_returns = values.pct_change().dropna()
        periods_per_year = PolymarketBacktester._estimate_periods_per_year(portfolio_history)

        if len(period_returns) > 1 and float(period_returns.std(ddof=1)) > 0:
            return_std = float(period_returns.std(ddof=1))
            sharpe_ratio = float(period_returns.mean()) / return_std * np.sqrt(periods_per_year)
            annualized_volatility = return_std * np.sqrt(periods_per_year)
        else:
            sharpe_ratio = 0.0
            annualized_volatility = 0.0

        first_timestamp = pd.to_datetime(portfolio_history["timestamp"].iloc[0], utc=True)
        last_timestamp = pd.to_datetime(portfolio_history["timestamp"].iloc[-1], utc=True)
        elapsed_years = max((last_timestamp - first_timestamp).total_seconds() / SECONDS_PER_YEAR, 0)
        if elapsed_years > 0 and final_value > 0:
            annualized_return = (final_value / initial_capital) ** (1 / elapsed_years) - 1.0
        else:
            annualized_return = cumulative_return

        running_peak = values.cummax()
        drawdowns = values / running_peak - 1.0
        max_drawdown = abs(float(drawdowns.min())) if not drawdowns.empty else 0.0

        sell_trades = [trade for trade in trades if trade.decision == "SELL" and trade.pnl is not None]
        winning_trades = sum(1 for trade in sell_trades if (trade.pnl or 0) > 0)
        losing_trades = sum(1 for trade in sell_trades if (trade.pnl or 0) < 0)

        return PolymarketBacktestMetrics(
            total_pnl=round(total_pnl, 6),
            cumulative_return=round(cumulative_return, 6),
            annualized_return=round(annualized_return, 6),
            sharpe_ratio=round(sharpe_ratio, 6),
            annualized_average_volatility=round(annualized_volatility, 6),
            max_drawdown=round(max_drawdown, 6),
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

    @staticmethod
    def _estimate_periods_per_year(portfolio_history: pd.DataFrame) -> float:
        timestamps = pd.to_datetime(portfolio_history["timestamp"], utc=True)
        deltas = timestamps.diff().dt.total_seconds().dropna()
        if deltas.empty:
            return TRADING_DAYS_PER_YEAR
        median_delta = float(deltas[deltas > 0].median())
        if not np.isfinite(median_delta) or median_delta <= 0:
            return TRADING_DAYS_PER_YEAR
        return SECONDS_PER_YEAR / median_delta


def run_polymarket_backtest(
    market_slug: str,
    rules: TradingRule | Iterable[TradingRule],
    outcome: str = "Yes",
    initial_capital: float = 1000.0,
    position_size: float | None = None,
    start: datetime | str | int | float | None = None,
    end: datetime | str | int | float | None = None,
    interval: str | None = None,
    fidelity: int | None = 1,
    enter_on_first_tick: bool = True,
    close_at_end: bool = True,
    client: PolymarketClient | None = None,
) -> PolymarketBacktestResult:
    """Convenience function for the common slug/outcome backtest flow."""
    config = PolymarketBacktestConfig(
        market_slug=market_slug,
        outcome=outcome,
        initial_capital=initial_capital,
        position_size=position_size,
        start=start,
        end=end,
        interval=interval,
        fidelity=fidelity,
        enter_on_first_tick=enter_on_first_tick,
        close_at_end=close_at_end,
    )
    return PolymarketBacktester(client=client).run(config=config, rules=rules)
