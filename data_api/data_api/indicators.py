import numpy as np
import pandas as pd

# ---- Moving Averages ----
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

# ---- RSI ----
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    dn = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))

# ---- ATR ----
def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift()
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1
    ).max(axis=1)
    return tr.rolling(n).mean()

# ---- Bollinger Bands ----
def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std()
    up = mid + k * sd
    low = mid - k * sd
    return mid, up, low

# ---- MACD ----
def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    f = ema(close, fast)
    s = ema(close, slow)
    line = f - s
    sig = ema(line, signal)
    hist = line - sig
    return line, sig, hist
