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
class TradingRuleConfig(BaseModel):
    id: str
    name: str
    ruleType: str
    timeframe: str
    changeType: Literal["price_increase", "price_decrease", "volume_increase", "volume_decrease"]
    changePercent: float
    decision: Literal["BUY", "SELL"]
    quantity: int
    enabled: bool

class BacktestRequest(BaseModel):
    stocks: List[str]
    startDate: str
    endDate: str
    initialCapital: float
    rules: List[TradingRuleConfig]

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


# ---- Backtest Endpoint ----

def _get_yf_interval(timeframe: str) -> str:
    """Map frontend timeframe to yfinance interval."""
    mapping = {
        "1Min": "1m",
        "5Min": "5m",
        "15Min": "15m",
        "30Min": "30m",
        "1H": "1h",
        "4H": "1h",  # yfinance doesn't have 4h, use 1h
        "1D": "1d",
        "1W": "1wk",
    }
    return mapping.get(timeframe, "1d")


@app.post("/backtest", response_model=BacktestResponse)
def run_backtest(config: BacktestRequest):
    """
    Run a backtest with the given configuration using real market data.
    """
    stocks = config.stocks
    start_date = config.startDate
    end_date = config.endDate
    initial_capital = config.initialCapital
    rules = [r for r in config.rules if r.enabled]

    if not stocks:
        raise HTTPException(status_code=400, detail="No stocks selected")
    if not rules:
        raise HTTPException(status_code=400, detail="No rules enabled")

    buy_rules = [r for r in rules if r.decision == "BUY"]
    sell_rules = [r for r in rules if r.decision == "SELL"]

    # Determine interval from rules (use the smallest timeframe)
    timeframes = [r.timeframe for r in rules]
    interval = _get_yf_interval(min(timeframes, key=lambda x: {
        "1Min": 1, "5Min": 5, "15Min": 15, "30Min": 30,
        "1H": 60, "4H": 240, "1D": 1440, "1W": 10080
    }.get(x, 1440)))

    # Fetch price data for all stocks
    stock_data: Dict[str, pd.DataFrame] = {}
    for stock in stocks:
        try:
            df = yf.download(stock, start=start_date, end=end_date, interval=interval, auto_adjust=False, progress=False)
            if df is None or df.empty:
                continue
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df = df.rename(columns={"Date": "timestamp", "Datetime": "timestamp"})
            df = df.sort_values("timestamp").reset_index(drop=True)
            stock_data[stock] = df
        except Exception as e:
            print(f"Error fetching {stock}: {e}")
            continue

    if not stock_data:
        raise HTTPException(status_code=404, detail="No price data available for the selected stocks and date range")

    # Initialize tracking
    trades: List[Trade] = []
    cash = initial_capital
    positions: Dict[str, dict] = {}  # {stock: {entry_price, quantity, entry_timestamp}}
    portfolio_values: List[float] = [initial_capital]
    timestamps: List[str] = [start_date]

    # Find the maximum length across all stock data
    max_length = max(len(df) for df in stock_data.values())

    # Run the backtest
    for i in range(1, max_length):
        for stock, df in stock_data.items():
            if i >= len(df):
                continue

            current = df.iloc[i]
            previous = df.iloc[i - 1]
            current_price = float(current["Close"])
            previous_price = float(previous["Close"])
            current_volume = float(current["Volume"])
            previous_volume = float(previous["Volume"])

            # Calculate changes
            price_change = ((current_price - previous_price) / previous_price) * 100 if previous_price > 0 else 0
            volume_change = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume > 0 else 0

            # Position P&L if holding
            position = positions.get(stock)
            position_pnl_pct = 0
            if position:
                position_pnl_pct = ((current_price - position["entry_price"]) / position["entry_price"]) * 100

            timestamp_str = str(current["timestamp"])[:19]

            # Evaluate BUY rules (only if not holding this stock)
            if stock not in positions:
                for rule in buy_rules:
                    triggered = False
                    if rule.changeType == "price_increase":
                        triggered = price_change >= rule.changePercent
                    elif rule.changeType == "price_decrease":
                        triggered = price_change <= -rule.changePercent
                    elif rule.changeType == "volume_increase":
                        triggered = volume_change >= rule.changePercent
                    elif rule.changeType == "volume_decrease":
                        triggered = volume_change <= -rule.changePercent

                    if triggered:
                        cost = current_price * rule.quantity
                        if cash >= cost:
                            cash -= cost
                            positions[stock] = {
                                "entry_price": current_price,
                                "quantity": rule.quantity,
                                "entry_timestamp": timestamp_str,
                            }
                            trades.append(Trade(
                                id=f"trade-{i}-{stock}-buy",
                                timestamp=timestamp_str,
                                stock=stock,
                                decision="BUY",
                                price=current_price,
                                quantity=rule.quantity,
                                ruleTriggered=rule.name,
                            ))
                            break

            # Evaluate SELL rules (only if holding this stock)
            if stock in positions:
                pos = positions[stock]
                for rule in sell_rules:
                    triggered = False
                    if rule.changeType == "price_increase":
                        triggered = position_pnl_pct >= rule.changePercent
                    elif rule.changeType == "price_decrease":
                        triggered = position_pnl_pct <= -rule.changePercent
                    elif rule.changeType == "volume_increase":
                        triggered = volume_change >= rule.changePercent
                    elif rule.changeType == "volume_decrease":
                        triggered = volume_change <= -rule.changePercent

                    if triggered:
                        revenue = current_price * pos["quantity"]
                        pnl = (current_price - pos["entry_price"]) * pos["quantity"]
                        cash += revenue
                        del positions[stock]
                        trades.append(Trade(
                            id=f"trade-{i}-{stock}-sell",
                            timestamp=timestamp_str,
                            stock=stock,
                            decision="SELL",
                            price=current_price,
                            quantity=pos["quantity"],
                            ruleTriggered=rule.name,
                            pnl=round(pnl, 2),
                        ))
                        break

        # Record portfolio value periodically
        if i % max(1, max_length // 100) == 0:
            portfolio_value = cash
            for stk, pos in positions.items():
                if stk in stock_data:
                    df = stock_data[stk]
                    idx = min(i, len(df) - 1)
                    portfolio_value += float(df.iloc[idx]["Close"]) * pos["quantity"]
            portfolio_values.append(round(portfolio_value, 2))
            # Get timestamp from any available stock
            for stk, df in stock_data.items():
                if i < len(df):
                    timestamps.append(str(df.iloc[i]["timestamp"])[:19])
                    break

    # Close remaining positions at end
    for stock, pos in list(positions.items()):
        if stock in stock_data:
            df = stock_data[stock]
            final_price = float(df.iloc[-1]["Close"])
            pnl = (final_price - pos["entry_price"]) * pos["quantity"]
            cash += final_price * pos["quantity"]
            trades.append(Trade(
                id=f"trade-final-{stock}",
                timestamp=str(df.iloc[-1]["timestamp"])[:19],
                stock=stock,
                decision="SELL",
                price=final_price,
                quantity=pos["quantity"],
                ruleTriggered="End of Backtest",
                pnl=round(pnl, 2),
            ))

    # Calculate metrics
    sell_trades = [t for t in trades if t.decision == "SELL" and t.pnl is not None]
    winning_trades = len([t for t in sell_trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in sell_trades if t.pnl and t.pnl < 0])
    total_pnl = sum(t.pnl or 0 for t in sell_trades)
    percent_return = ((cash - initial_capital) / initial_capital) * 100

    # Calculate max drawdown
    peak = initial_capital
    max_drawdown = 0
    for value in portfolio_values:
        if value > peak:
            peak = value
        drawdown = ((peak - value) / peak) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    portfolio_values.append(round(cash, 2))
    timestamps.append(end_date)

    return BacktestResponse(
        totalTrades=len(trades),
        winningTrades=winning_trades,
        losingTrades=losing_trades,
        totalPnL=round(total_pnl, 2),
        percentReturn=round(percent_return, 2),
        maxDrawdown=round(max_drawdown, 2),
        trades=[t.model_dump() for t in trades],
        portfolioValue=portfolio_values,
        timestamps=timestamps,
    )
