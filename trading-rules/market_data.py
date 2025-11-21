import pandas as pd

PRICE = 'price'

class MarketData:
    """
    A class to represent market data in dataframe format.
    """
    def __init__(self, **kwargs):
        self.df = pd.DataFrame(kwargs)
        self.columns = kwargs.keys()

    def get_latest_price(self):
        return self.df[PRICE].iloc[-1]
    
    def get_mean(self, window):
        return self.df[PRICE].rolling(window=window).mean().iloc[-1]

    def __repr__(self):
        return f"MarketData(symbol={self.symbol}, price={self.price}, volume={self.volume})"