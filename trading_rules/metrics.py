import numpy as np
import pandas as pd


class Metrics:
    """Performance metrics for a backtest run.

    Args:
        trades: List of dicts produced by the engine, each containing
                entry_price, qty, entry_idx, exit_price and exit_idx.
        equity: Portfolio value over time, indexed by timestamp.
    """

    def __init__(self, trades: list[dict], equity: pd.Series):
        self.trades = trades
        self.equity = equity

    def returns(self) -> pd.Series:
        """Simple per-bar returns of the equity curve."""
        return self.equity.pct_change().dropna()

    def log_returns(self) -> pd.Series:
        """Per-bar log returns of the equity curve."""
        return np.log(self.equity / self.equity.shift(1)).dropna()

    def sharpe_ratio(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
        """Annualized Sharpe ratio computed from daily returns.

        The equity curve is resampled to daily (end-of-day mark) so the ratio
        is comparable regardless of the underlying bar frequency.

        Args:
            risk_free_rate: Annualized risk-free rate (e.g. 0.04 for 4%).
                            Converted to a per-day rate internally.
            periods_per_year: Trading periods in a year used for annualization.
                              Use 252 for daily equity data, 365 for crypto.
        """
        daily_value = self.equity.resample("1D").last().dropna()
        daily_returns = daily_value.pct_change().dropna()

        period_risk_free = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

        excess_returns = daily_returns - period_risk_free
        std_excess = excess_returns.std(ddof=1)

        if std_excess == 0 or np.isnan(std_excess):
            return float("nan")

        return (excess_returns.mean() / std_excess) * np.sqrt(periods_per_year)

    def annualized_cumulative_return(self) -> float:
        """Compound annual growth rate (CAGR) of the equity curve."""
        initial_amount = self.equity.iloc[0]
        final_amount = self.equity.iloc[-1]

        years = (
            self.equity.index[-1] - self.equity.index[0]
        ).total_seconds() / (365.25 * 24 * 3600)

        return (final_amount / initial_amount) ** (1 / years) - 1

    def max_drawdown(self) -> float:
        """Largest peak-to-trough decline as a negative fraction (e.g. -0.25)."""
        running_peak = self.equity.cummax()
        drawdowns = self.equity / running_peak - 1
        return drawdowns.min()

    def summary(self, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> pd.DataFrame:
        """Compute all scalar metrics and return them as a one-row DataFrame."""
        stats = {
            "Total Return": self.equity.iloc[-1] / self.equity.iloc[0] - 1,
            "CAR": self.annualized_cumulative_return(),
            "Sharpe": self.sharpe_ratio(risk_free_rate, periods_per_year),
            "Max Drawdown": self.max_drawdown(),
            "Trades": len(self.trades),
        }
        return pd.DataFrame([stats])
