from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
import pandas as pd
import yfinance as yf
from datetime import datetime

from .indicators import sma, ema, rsi, atr, bollinger, macd

app = FastAPI(title="Systematic Trader Data API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Pydantic Models for Backtest ----
class RuleParams(BaseModel):
    """Parameters for Python trading rules"""
    shortWindow: Optional[int] = 5
    longWindow: Optional[int] = 20
    profitThreshold: Optional[float] = 0.02
    lossThreshold: Optional[float] = 0.02

class TradingRuleConfig(BaseModel):
    id: str
    name: str
    ruleType: str
    timeframe: str
    changeType: Optional[Literal["price_increase", "price_decrease", "volume_increase", "volume_decrease"]] = None
    changePercent: Optional[float] = None
    decision: Literal["BUY", "SELL"]
    quantity: int
    enabled: bool
    # New fields for Python trading rules
    pythonRuleType: Optional[str] = None  # mean_reversal, early_profit_taker, etc.
    params: Optional[RuleParams] = None

class BacktestRequest(BaseModel):
    stocks: List[str]
    startDate: str
    endDate: str
    initialCapital: float
    rules: List[TradingRuleConfig]
    quantityPerTrade: Optional[int] = 100

class Trade(BaseModel):
    id: str
    timestamp: str
    stock: str
    decision: str
    price: float
    quantity: int
    ruleTriggered: str
    pnl: Optional[float] = None

class BacktestResponse(BaseModel):
    totalTrades: int
    winningTrades: int
    losingTrades: int
    totalPnL: float
    percentReturn: float
    maxDrawdown: float
    trades: List[Trade]
    portfolioValue: List[float]
    timestamps: List[str]

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
def _fetch_history(
    ticker: str,
    start: Optional[str],
    end: Optional[str],
    interval: str
) -> pd.DataFrame:
    if interval not in INTERVAL_LIMITS:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_INTERVAL", "allowed": list(INTERVAL_LIMITS.keys())}
        )

    # Safer yfinance call: disable threads and catch errors
    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,  # <- important: avoids some YFTzMissingError / timezone issues
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "YFINANCE_ERROR",
                "ticker": ticker,
                "reason": str(e),
            },
        )

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail={"code": "TICKER_NOT_FOUND", "ticker": ticker}
        )

    # Normalize columns + index
    df = df.rename(columns=str.title)
    df = df.reset_index()

    # yfinance usually uses "Date" for 1d and "Datetime" for intraday
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "timestamp"})
    elif "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "timestamp"})
    else:
        # Unexpected schema; surface it clearly
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INVALID_DATA_FORMAT",
                "ticker": ticker,
                "columns": df.columns.tolist(),
            },
        )

    # Keep standard schema
    cols = ["timestamp", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for c in cols:
        if c not in df.columns:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "MISSING_COLUMN",
                    "column": c,
                    "ticker": ticker,
                    "columns": df.columns.tolist(),
                },
            )

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
        need = max(
            need,
            int(p.get("macd_slow", 26)),
            int(p.get("macd_fast", 12)),
            int(p.get("macd_signal", 9)),
        )
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
        raise HTTPException(
            status_code=422,
            detail={"code": "INSUFFICIENT_DATA", "need_bars": int(need)}
        )

    df = _apply_indicators(df, want_list, params)
    if format == "csv":
        return PlainTextResponse(df.to_csv(index=False))
    return JSONResponse(df.to_dict(orient="records"))


# ---- Backtest Endpoint ----

@app.post("/backtest", response_model=BacktestResponse)
def run_backtest_endpoint(config: BacktestRequest):
    """
    Run a backtest with the given configuration using real market data.
    Supports both simple rules and Python trading_rules module.
    """
    from .backtest_service import run_backtest, TradeRecord

    stocks = config.stocks
    start_date = config.startDate
    end_date = config.endDate
    initial_capital = config.initialCapital
    quantity_per_trade = config.quantityPerTrade or 100

    # Convert Pydantic models to dicts for the service
    rules = []
    for r in config.rules:
        rule_dict = {
            "id": r.id,
            "name": r.name,
            "ruleType": r.ruleType,
            "timeframe": r.timeframe,
            "changeType": r.changeType,
            "changePercent": r.changePercent,
            "decision": r.decision,
            "quantity": r.quantity,
            "enabled": r.enabled,
            "pythonRuleType": r.pythonRuleType,
            "params": r.params.model_dump() if r.params else None
        }
        rules.append(rule_dict)

    if not stocks:
        raise HTTPException(status_code=400, detail="No stocks selected")
    if not rules:
        raise HTTPException(status_code=400, detail="No rules configured")

    enabled_rules = [r for r in rules if r.get("enabled", True)]
    if not enabled_rules:
        raise HTTPException(status_code=400, detail="No rules enabled")

    try:
        result = run_backtest(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            rules=enabled_rules,
            quantity_per_trade=quantity_per_trade
        )

        # Convert TradeRecord objects to Trade dicts
        trades = []
        for t in result.trades:
            trades.append({
                "id": t.id,
                "timestamp": t.timestamp,
                "stock": t.stock,
                "decision": t.decision,
                "price": t.price,
                "quantity": t.quantity,
                "ruleTriggered": t.rule_triggered,
                "pnl": t.pnl
            })

        return BacktestResponse(
            totalTrades=result.total_trades,
            winningTrades=result.winning_trades,
            losingTrades=result.losing_trades,
            totalPnL=result.total_pnl,
            percentReturn=result.percent_return,
            maxDrawdown=result.max_drawdown,
            trades=trades,
            portfolioValue=result.portfolio_values,
            timestamps=result.timestamps,
        )

    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
