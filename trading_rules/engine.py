import pandas as pd

OPEN = 'open'
CLOSE = 'close'
HIGH = 'high'
LOW = 'low'
VOLUME = 'volume'

def validate(data: pd.DataFrame) -> pd.DataFrame:
    required = [OPEN, HIGH, LOW, CLOSE, VOLUME]
    
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    
    if data[CLOSE].isna().all():
        raise RuntimeError("Close column is entirely NaN after conversion")
    
    return data

def backtest(data: pd.DataFrame, entries_series: pd.Series, exits_list: list[callable], initial_cash: float):
    
    validate(data)
    
    cash = initial_cash
    pos = None
    trades, equity = [], []
    size_frac = 1.0 # Use all the cash available

    for i in range(len(data)):
        price = data.iloc[i]['close']

        # Check if we are holding securities
        if pos is not None:
            # Check for selling signals, if any of them return True, SELL!!!
            if any(rule(pos, price, data, i) for rule in exits_list):
                cash += pos["qty"] * price
                trades.append({**pos, "exit_price": price, "exit_idx": i})
                pos = None
        
        # Check for buying signals, if this bar evaluates to TRUE, BUY!!!
        elif entries_series.iloc[i]:
            qty = (cash * size_frac) / price
            cash -= qty * price
            pos = {"entry_price": price, "qty": qty, "entry_idx": i}

        equity.append(cash + (pos["qty"] * price if pos else 0))

    return {"equity": pd.Series(equity, index=data.index), "trades": trades}