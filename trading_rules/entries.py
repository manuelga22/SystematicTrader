import pandas as pd

CLOSE = 'close'

def mean_reversion(data: pd.DataFrame, window: int, z_score: float = None) -> pd.Series:

    if data.empty:
        raise RuntimeError("No data was provided")
    
    mean = data[CLOSE].rolling(window=window).mean()

    if z_score is not None:
        std = data[CLOSE].rolling(window=window).std()
        z = (data[CLOSE] - mean) / std
        return (z < z_score).fillna(False)
    else:
        return (data[CLOSE] < mean).fillna(False)