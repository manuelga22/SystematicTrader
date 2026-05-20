import pandas as pd
from trading_rules.position_data import Positions, PositionData, BUY, SELL
from trading_rules.market_data import MarketData

class PortfolioPerformance:

    def __init__(self, positions: Positions, initial_cash: float, market_data: MarketData):
        self.positions = positions
        self.initial_cash = initial_cash
        self.market_data = market_data

    def get_daily_returns_history(self, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
        """Build a daily returns dataframe for a portfolio between start_ts and end_ts.

        prices: index = daily timestamps (normalized), columns = symbols, values = price per unit.
                Used to mark-to-market open positions on each day.

        Returns a DataFrame indexed by day with columns:
            cash, holdings_value, portfolio_value, daily_return
        """
        trades: list[PositionData] = self.positions.get_transaction_history()
        # self.market_data_df = self.market_data_df.resample("D").last()

        market_data_df = self.market_data.df.loc[start_ts:end_ts]

        rows = []
        for time, _ in market_data_df.iterrows():

            newest_transaction_for_t = self._find_newest_transaction_before(trades, time)
            holdings_dict = self.positions.get_holdings_at_time(time)

            portfolio_value = 0
            for sym, quantity in holdings_dict.items():
                sym_price_at_ts = self.market_data.get_price_at_time(sym, time)
                portfolio_value += (sym_price_at_ts * quantity)

            rows.append({
                "timestamp": time,
                "cash_balance": newest_transaction_for_t.cash_balance if newest_transaction_for_t else self.initial_cash,
                "portfolio_value": portfolio_value
            })

        df = pd.DataFrame(rows).set_index("timestamp")

        # pct_change vs. previous day's close; day-0 compares against initial_cash.
        prev_value = df["portfolio_value"].shift(1)
        prev_value.iloc[0] = self.initial_cash
        df["daily_return"] = (df["portfolio_value"] - prev_value) / prev_value

        return df
    
    def get_daily_returns_history_by_security(self, symbol: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
        pass

    def get_trading_history(self) -> pd.DataFrame:
        """Parse positions into a dataframe for easier analysis."""

        trading_history: list[PositionData] = self.positions.get_transaction_history()
        trading_history_df = pd.DataFrame(columns=['symbol', 'quantity', 'price', 'action', 'timestamp'])

        for trades in trading_history:
            trade_dict = {
                "symbol": trades.symbol,
                "quantity": trades.quantity,
                "price": trades.action,
                "timestamp": trades.timestamp
            }
            new_trade = pd.DataFrame(trade_dict)
            trading_history_df.append(new_trade, ignore_index=True)

        return trading_history_df
    
    def _find_newest_transaction_before(self, trades: list[PositionData], ts: pd.Timestamp):
        
        newest_transation = None
        for t in trades:
            time = t.get_timestamp()

            if time <= ts:
                newest_transation = t
            else:
                break

        return newest_transation 
