import pandas as pd

OPEN = 'open'
CLOSE = 'close'
HIGH = 'high'
LOW = 'low'
VOLUME = 'volume'
ATR = 'atr' # average true range.


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    df must have columns: high, low, close
    Returns a Series of ATR values aligned to df.index.
    """
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()