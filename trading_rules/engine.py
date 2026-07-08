import pandas as pd
from trading_rules.fees import FeeParams, taker_fees
from trading_rules.fills import SlippageParams, OrderFiller
import trading_rules.common as common
from trading_rules.common import HIGH, CLOSE, LOW, ATR, VOLUME, OPEN


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

def backtest(data: pd.DataFrame, entries_series: pd.Series, exits_list: list[callable], 
             initial_cash: float, fee_params: FeeParams, slippage_params: SlippageParams):
    
    validate(data)

    # add the average true range, this helps make slippage more accurate.
    data[ATR] = common.compute_atr(data)
    
    cash = initial_cash
    pos = None
    trades, equity = [], []
    size_frac = 1.0 # Use all the cash available

    order_filler = OrderFiller(data, slippage_params)
    

    for i in range(len(data)):
        price = data.iloc[i]['close']

        # Check if we are holding securities
        if pos is not None:
            # Check for selling signals, if any of them return True, SELL!!!
            if any(rule(pos, price, data, i) for rule in exits_list):
                fill_price = order_filler.fill_price(i, -1)
                exit_fee = taker_fees(pos["qty"], fill_price, fee_params)
                cash += pos["qty"] * fill_price - exit_fee
                trades.append({**pos, "exit_price": fill_price, "exit_idx": i, "exit_fee": exit_fee})
                pos = None

        # Check for buying signals, if this bar evaluates to TRUE, BUY!!!
        elif entries_series.iloc[i]:
            budget = cash * size_frac
            fill_price = order_filler.fill_price(i, 1)
            qty = budget / fill_price
            entry_fee = taker_fees(qty, fill_price, fee_params)

            if entry_fee > 0:
                # Shrink the order so shares + fee fit inside the budget.
                # The fee is estimated on the pre-shrink qty, so this slightly
                # overcharges and never overspends.
                qty = (budget - entry_fee) / fill_price
                entry_fee = taker_fees(qty, fill_price, fee_params)


            if qty > 0:
                cash -= qty * fill_price + entry_fee
                pos = {"entry_price": fill_price, "qty": qty, "entry_idx": i, "entry_fee": entry_fee}

        equity.append(cash + (pos["qty"] * price if pos else 0))

    return {"equity": pd.Series(equity, index=data.index), "trades": trades}