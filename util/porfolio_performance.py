import numpy as np
import pandas as pd
from trading_rules.position_data import Positions, PositionData, BUY, SELL
from trading_rules.market_data import MarketData

SIMPLE_RETURNS = "simple_returns"
LOG_RETURNS = "log_returns"
TOTAL_VALUE = "total_value"
TIMESTAMP = "timestamp"
CASH_BALANCE = "cash_balance"

class PortfolioPerformance:

    def __init__(self, positions: Positions, initial_cash: float, market_data: MarketData):
        self.positions = positions
        self.initial_cash = initial_cash
        self.market_data = market_data

    def get_returns_history(self) -> pd.DataFrame:
        """Build a returns dataframe for a portfolio between start_ts and end_ts.

        prices: index = daily timestamps (normalized), columns = symbols, values = price per unit.
                Used to mark-to-market open positions on each day.

        Returns a DataFrame indexed by day with columns:
            cash, holdings_value, portfolio_value, daily_return
        """
        trades: list[PositionData] = self.positions.get_transaction_history()

        market_data_df = self.market_data.df

        rows = []
        for time, _ in market_data_df.iterrows():

            newest_transaction_for_t = self._find_newest_transaction_before(trades, time)
            holdings_dict = self.positions.get_holdings_at_time(time)

            portfolio_value = 0
            for sym, quantity in holdings_dict.items():
                sym_price_at_ts = self.market_data.get_price_at_time(sym, time)
                portfolio_value += (sym_price_at_ts * quantity)

            rows.append({
                TIMESTAMP: time,
                CASH_BALANCE: newest_transaction_for_t.cash_balance if newest_transaction_for_t else self.initial_cash,
                "portfolio_value": portfolio_value
            })

        df = pd.DataFrame(rows).set_index(TIMESTAMP)

        # Total portfolio value = cash + market value of holdings.
        df[TOTAL_VALUE] = df[CASH_BALANCE] + df["portfolio_value"]
        prev_total = df[TOTAL_VALUE].shift(1)
        # pct_change vs. previous period's total value; period-0 compares against initial_cash.
        prev_total.iloc[0] = self.initial_cash

        df[SIMPLE_RETURNS] = (df[TOTAL_VALUE] - prev_total) / prev_total
        df[LOG_RETURNS] = np.log(df[TOTAL_VALUE]).diff()

        return df
    
    def get_trading_history(self) -> pd.DataFrame:
        """Parse positions into a dataframe for easier analysis."""

        trading_history: list[PositionData] = self.positions.get_transaction_history()
        trading_history_df = pd.DataFrame(columns=['symbol', 'quantity', 'price', 'action', 'timestamp'])

        for trades in trading_history:
            trade_dict = {
                "symbol": trades.symbol,
                "quantity": trades.quantity,
                "price": trades.action,
                TIMESTAMP: trades.timestamp
            }
            new_trade = pd.DataFrame(trade_dict)
            trading_history_df.append(new_trade, ignore_index=True)

        return trading_history_df
    
    @ staticmethod
    def get_annualized_sharpe_ratio(
        returns_df,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """Calculate the annualized Sharpe ratio for the portfolio.

        Args:
            start_ts: Start of the evaluation window.
            end_ts: End of the evaluation window.
            risk_free_rate: Annualized risk-free rate (e.g. 0.04 for 4%).
                            Converted to a per-period rate internally.
            periods_per_year: Trading periods in a year used for annualization.
                              Use 252 for daily equity data, 365 for crypto, etc.

        Returns:
            Annualized Sharpe ratio as a float. Returns NaN if standard
            deviation of returns is zero.
        """

        if TOTAL_VALUE not in returns_df:
            raise IndexError(f"{TOTAL_VALUE} not present in returns_df")

        # Resample portfolio value to daily (end-of-day mark) so that Sharpe is
        # computed on daily returns regardless of the underlying bar frequency.
        # The paper computes Sharpe from daily returns annualized with sqrt(252).
        daily_value = returns_df[TOTAL_VALUE].resample("1D").last().dropna()
        daily_returns = daily_value.pct_change().dropna()

        # Convert annualized risk-free rate to a per-period (daily) rate.
        period_risk_free = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

        excess_returns = daily_returns - period_risk_free
        mean_excess = excess_returns.mean()
        std_excess = excess_returns.std(ddof=1)

        if std_excess == 0 or np.isnan(std_excess):
            return float("nan")

        sharpe = (mean_excess / std_excess) * np.sqrt(periods_per_year)
        return sharpe



    @staticmethod
    def get_annualized_cumulative_return(returns_df: pd.DataFrame):
        pass
    
    def _find_newest_transaction_before(self, trades: list[PositionData], ts: pd.Timestamp):
        
        newest_transation = None
        for t in trades:
            time = t.get_timestamp()

            if time <= ts:
                newest_transation = t
            else:
                break

        return newest_transation 
