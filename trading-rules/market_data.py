import pandas as pd

class MarketData:
    """
    A class to represent market data in dataframe format.
    """
    def __init__(self, **kwargs):
        self.df = pd.DataFrame(kwargs)
        self.columns = kwargs.keys()

    def __repr__(self):
        return f"MarketData(symbol={self.symbol}, price={self.price}, volume={self.volume})"