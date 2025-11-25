from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
import yfinance as yf

from .indicators import sma, ema, rsi, atr, bollinger, macd

app = FastAPI(title="Systematic Trader Data API", version="0.1.0")

# Practical interval limits (days) for yfinance
INTERVAL_LIMITS = {
    "1m": 7,    # ~1 week
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 730, # ~2 years
    "90m": 730,
    "1h": 730,  # alias often mapped to 60m
    "1d": 36500,
    "5d": 36500,
    "1wk": 36500,
    "1mo": 36500,
    "3mo": 36500,
}

# ---- Helpers ----------------------------------------------------------------
def _fetch_history(ticker: str, start: Optional[str], end: Optional[str], interval: str) -> pd.DataFrame:
    if interval not in INTERVAL_LIMITS:
        raise HTTPException(status_code=400, detail={"code": "BAD_INTERVAL", "allowed": list(INTERVAL_LIMITS.keys())})

    df = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail={"code": "TICKER_NOT_FOUND", "ticker": ticker})

    # Normalize columns + index
    df = df.rename(columns=str.title)
    df = df.reset_index().rename(columns={"Date": "timestamp"})
    # Keep standard schema
    cols = ["timestamp", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    df = df[cols]
    # sort ascending just in case
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def _max_lookback_needed(indicators: List[str], p: Dict) -> int:
    """Return how many bars are needed at minimum for the requested indicators."""
    need = 1
    L = [s.strip().lower() for s in indicators]
    if "sma" in L:
        need = max(need, int(p.get("sma_window", 50)), int(p.get("sma_window2", 200)))
    if "ema" in L:
        need = max(need, int(p.get("ema_window", 20)))
    if "rsi" in L:
        need = max(need, int(p.get("rsi_len", 14)))
    if "atr" in L:
        need = max(need, int(p.get("atr_len", 14)))
    if "bollinger" in L:
        need = max(need, int(p.get("bb_window", 20)))
    if "macd" in L:
        need = max(need, int(p.get("macd_slow", 26)), int(p.get("macd_fast", 12)), int(p.get("macd_signal", 9)))
    return need

def _apply_indicators(df: pd.DataFrame, indicators: List[str], p: Dict) -> pd.DataFrame:
    L = [s.strip().lower() for s in indicators]
    close = df["Close"]; high = df["High"]; low = df["Low"]

    if "sma" in L:
        w1 = int(p.get("sma_window", 50))
        w2 = int(p.get("sma_window2", 200))
        df[f"SMA_{w1}"] = sma(close, w1)
        df[f"SMA_{w2}"] = sma(close, w2)
    if "ema" in L:
        w = int(p.get("ema_window", 20))
        df[f"EMA_{w}"] = ema(close, w)
    if "rsi" in L:
        n = int(p.get("rsi_len", 14))
        df[f"RSI_{n}"] = rsi(close, n)
    if "atr" in L:
        n = int(p.get("atr_len", 14))
        df[f"ATR_{n}"] = atr(high, low, close, n)
    if "bollinger" in L:
        n = int(p.get("bb_window", 20))
        k = float(p.get("bb_std", 2.0))
        mid, up, lowb = bollinger(close, n, k)
        df[f"BB_MID_{n}"] = mid
        df[f"BB_UP_{n}_{k}"] = up
        df[f"BB_LOW_{n}_{k}"] = lowb
    if "macd" in L:
        fast = int(p.get("macd_fast", 12))
        slow = int(p.get("macd_slow", 26))
        sig  = int(p.get("macd_signal", 9))
        line, sigl, hist = macd(close, fast, slow, sig)
        df["MACD"] = line
        df["MACD_SIGNAL"] = sigl
        df["MACD_HIST"] = hist
    return df

# ---- Routes -----------------------------------------------------------------

@app.get("/meta/limits")
def meta_limits():
    """Return supported intervals and rough max lookback (days) so the GUI can clamp controls."""
    return {"interval_limits_days": INTERVAL_LIMITS}

@app.get("/history")
def history(
    ticker: str = Query(..., description="Ticker symbol, e.g., AAPL"),
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    interval: str = Query("1d"),
    format: str = Query("json", regex="^(json|csv)$")
):
    """
    Return raw OHLCV (+ Adj Close) for a ticker and period.
    """
    df = _fetch_history(ticker, start, end, interval)
    if format == "csv":
        return PlainTextResponse(df.to_csv(index=False))
    return JSONResponse(df.to_dict(orient="records"))

@app.get("/indicators")
def indicators(
    ticker: str = Query(..., description="Ticker symbol, e.g., AAPL"),
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    interval: str = Query("1d"),
    indicators: str = Query("sma,rsi,atr", description="Comma-separated: sma,ema,rsi,atr,bollinger,macd"),
    # Common params (sliders can set these)
    sma_window: int = 50,
    sma_window2: int = 200,
    ema_window: int = 20,
    rsi_len: int = 14,
    atr_len: int = 14,
    bb_window: int = 20,
    bb_std: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    format: str = Query("json", regex="^(json|csv)$")
):
    """
    Return OHLCV plus the requested indicators as columns.
    """
    want_list = [w.strip() for w in indicators.split(",") if w.strip()]
    params = dict(
        sma_window=sma_window, sma_window2=sma_window2, ema_window=ema_window,
        rsi_len=rsi_len, atr_len=atr_len, bb_window=bb_window, bb_std=bb_std,
        macd_fast=macd_fast, macd_slow=macd_slow, macd_signal=macd_signal
    )

    df = _fetch_history(ticker, start, end, interval)

    # guard: ensure enough bars for the longest lookback requested
    need = _max_lookback_needed(want_list, params)
    if len(df) < need:
        raise HTTPException(status_code=422, detail={"code": "INSUFFICIENT_DATA", "need_bars": int(need)})

    df = _apply_indicators(df, want_list, params)
    if format == "csv":
        return PlainTextResponse(df.to_csv(index=False))
    return JSONResponse(df.to_dict(orient="records"))
