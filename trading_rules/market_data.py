import pandas as pd
import numpy as np

PRICE = 'close'

class MarketData:
    """
    A class to represent market data in dataframe format.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.columns = df.columns.tolist()

    def get_latest_price(self):
        return self.df[PRICE].iloc[-1]
    
    def get_mean(self, window):
        return self.df[PRICE].rolling(window=window).mean().iloc[-1]
    
    def get_std(self, window):
        return self.df[PRICE].rolling(window=window).std().iloc[-1]
    
    def get_returns(self, column="close"):
        self.df['returns'] = self.df[column].pct_change()
        return self.df['returns']
    
    def get_log_returns(self, column="close"):
        self.df['log_returns'] = np.log(self.df[column] / self.df[column].shift(1))
        return self.df['log_returns']
