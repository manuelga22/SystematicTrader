import pandas as pd

CLOSE = 'close'

def mean_reversion(data: pd.DataFrame, window: int) -> pd.Series:

    if data.empty:
        raise RuntimeError("No data was provided")
    
    rolling_min = data[CLOSE].rolling(window=window).min().shift(1)
    return (data[CLOSE] <= rolling_min).fillna(False)
    

def mean_reversion_z_score(data: pd.DataFrame, window: int, z_score: float):

    
    if data.empty:
        raise RuntimeError("No data was provided")

    mean = data[CLOSE].rolling(window=window)
    std = data[CLOSE].rolling(window=window).std()
    z = (data[CLOSE] - mean) / std
    return (z < z_score).fillna(False)
