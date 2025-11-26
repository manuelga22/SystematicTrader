"""
Backtest service that uses the actual trading_rules module.
"""
import sys
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import yfinance as yf

# Add trading_rules to path - need to add both the project root and trading_rules dir
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
trading_rules_dir = os.path.join(project_root, 'trading_rules')
sys.path.insert(0, project_root)
sys.path.insert(0, trading_rules_dir)

# Now import the trading rules modules
from market_data import MarketData
from position_data import Positions, PositionData
from signals import TradingSignalEnum
from mean_reversal import MeanReversal
from early_profit_taker import EarlyProfitTaker
from early_loss_taker import EarlyLossTaker
from loss_profit_taker import LossProfitTaker


class RuleType(str, Enum):
    # Entry rules (BUY)
    MEAN_REVERSAL = "mean_reversal"
    PRICE_DIP = "price_dip"  # Simple price decrease trigger
    PRICE_MOMENTUM = "price_momentum"  # Simple price increase trigger

    # Exit rules (SELL)
    EARLY_PROFIT_TAKER = "early_profit_taker"
    EARLY_LOSS_TAKER = "early_loss_taker"
    LOSS_PROFIT_TAKER = "loss_profit_taker"


@dataclass
class TradeRecord:
    id: str
    timestamp: str
    stock: str
    decision: str
    price: float
    quantity: int
    rule_triggered: str
    pnl: Optional[float] = None


@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    percent_return: float
    max_drawdown: float
    trades: List[TradeRecord]
    portfolio_values: List[float]
    timestamps: List[str]


def create_rule_from_config(config: dict):
    """
    Create a TradingRule instance from frontend configuration.
    Returns one of: MeanReversal, EarlyProfitTaker, EarlyLossTaker, LossProfitTaker, or None.
    """
    rule_type = config.get("pythonRuleType", "")
    params = config.get("params", {})

    if rule_type == RuleType.MEAN_REVERSAL:
        return MeanReversal(
            short_window=params.get("shortWindow", 5),
            long_window=params.get("longWindow", 20)
        )
    elif rule_type == RuleType.EARLY_PROFIT_TAKER:
        return EarlyProfitTaker(
            profit_threshold=params.get("profitThreshold", 0.02)
        )
    elif rule_type == RuleType.EARLY_LOSS_TAKER:
        return EarlyLossTaker(
            loss_threshold=params.get("lossThreshold", 0.02)
        )
    elif rule_type == RuleType.LOSS_PROFIT_TAKER:
        return LossProfitTaker(
            loss_threshold=params.get("lossThreshold", 0.02),
            won_threshold=params.get("profitThreshold", 0.02)
        )

    return None


def fetch_stock_data(stock: str, start_date: str, end_date: str, interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Fetch historical stock data using yfinance.
    """
    try:
        df = yf.download(stock, start=start_date, end=end_date, interval=interval,
                        auto_adjust=False, progress=False)
        if df is None or df.empty:
            return None

        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df = df.rename(columns={"Date": "timestamp", "Datetime": "timestamp"})
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Rename to lowercase for MarketData compatibility
        df = df.rename(columns={"Close": "price", "Volume": "volume",
                                "Open": "open", "High": "high", "Low": "low"})
        return df
    except Exception as e:
        print(f"Error fetching {stock}: {e}")
        return None


def run_backtest(
    stocks: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float,
    rules: List[dict],
    quantity_per_trade: int = 100
) -> BacktestResult:
    """
    Run a backtest using the actual trading_rules module.
    """
    # Separate rules by type
    buy_rules_config = [r for r in rules if r.get("enabled", True) and r.get("decision") == "BUY"]
    sell_rules_config = [r for r in rules if r.get("enabled", True) and r.get("decision") == "SELL"]

    # Check for Python rule types vs simple rules
    python_buy_rules = []
    python_sell_rules = []
    simple_buy_rules = []
    simple_sell_rules = []

    for r in buy_rules_config:
        python_rule = create_rule_from_config(r)
        if python_rule:
            python_buy_rules.append((r, python_rule))
        else:
            simple_buy_rules.append(r)

    for r in sell_rules_config:
        python_rule = create_rule_from_config(r)
        if python_rule:
            python_sell_rules.append((r, python_rule))
        else:
            simple_sell_rules.append(r)

    # Fetch stock data
    stock_data: Dict[str, pd.DataFrame] = {}
    for stock in stocks:
        df = fetch_stock_data(stock, start_date, end_date)
        if df is not None and len(df) > 0:
            stock_data[stock] = df

    if not stock_data:
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=0,
            percent_return=0,
            max_drawdown=0,
            trades=[],
            portfolio_values=[initial_capital],
            timestamps=[start_date]
        )

    # Initialize tracking
    trades: List[TradeRecord] = []
    cash = initial_capital
    positions = Positions(cash=initial_capital)
    held_stocks: Dict[str, dict] = {}  # Track positions per stock
    portfolio_values: List[float] = [initial_capital]
    timestamps: List[str] = [start_date]

    # Find max length across stock data
    max_length = max(len(df) for df in stock_data.values())

    # Minimum window needed for mean reversal
    min_window = 20
    for r in buy_rules_config:
        if r.get("pythonRuleType") == RuleType.MEAN_REVERSAL:
            params = r.get("params", {})
            min_window = max(min_window, params.get("longWindow", 20))

    # Run backtest
    for i in range(min_window, max_length):
        for stock, df in stock_data.items():
            if i >= len(df):
                continue

            current = df.iloc[i]
            previous = df.iloc[i - 1]
            current_price = float(current["price"])
            previous_price = float(previous["price"])
            timestamp_str = str(current["timestamp"])[:19]

            # Calculate simple price change
            price_change_pct = ((current_price - previous_price) / previous_price) * 100 if previous_price > 0 else 0

            # Create MarketData for this stock (use last N rows for moving averages)
            lookback_df = df.iloc[max(0, i - min_window):i + 1].copy()
            market_data = MarketData(lookback_df)

            # Update positions object for signal generation
            temp_positions = Positions(cash=cash)
            if stock in held_stocks:
                pos = held_stocks[stock]
                temp_positions.positions.append(
                    PositionData(stock, pos["quantity"], pos["entry_price"])
                )

            # Check BUY signals (only if not holding this stock)
            if stock not in held_stocks:
                buy_triggered = False
                triggered_rule_name = ""

                # Check Python rules first
                for rule_config, rule in python_buy_rules:
                    signal = rule.generate_signal(market_data, temp_positions)
                    if signal == TradingSignalEnum.BUY:
                        buy_triggered = True
                        triggered_rule_name = rule_config.get("name", "Python Rule")
                        break

                # Check simple rules if no Python rule triggered
                if not buy_triggered:
                    for rule_config in simple_buy_rules:
                        change_type = rule_config.get("changeType", "")
                        threshold = rule_config.get("changePercent", 2)

                        if change_type == "price_decrease" and price_change_pct <= -threshold:
                            buy_triggered = True
                            triggered_rule_name = rule_config.get("name", "Price Dip")
                            break
                        elif change_type == "price_increase" and price_change_pct >= threshold:
                            buy_triggered = True
                            triggered_rule_name = rule_config.get("name", "Price Momentum")
                            break

                if buy_triggered:
                    qty = quantity_per_trade
                    cost = current_price * qty
                    if cash >= cost:
                        cash -= cost
                        held_stocks[stock] = {
                            "entry_price": current_price,
                            "quantity": qty,
                            "entry_timestamp": timestamp_str
                        }
                        trades.append(TradeRecord(
                            id=f"trade-{i}-{stock}-buy",
                            timestamp=timestamp_str,
                            stock=stock,
                            decision="BUY",
                            price=current_price,
                            quantity=qty,
                            rule_triggered=triggered_rule_name
                        ))

            # Check SELL signals (only if holding this stock)
            if stock in held_stocks:
                pos = held_stocks[stock]
                position_pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100

                sell_triggered = False
                triggered_rule_name = ""

                # Check Python rules first
                for rule_config, rule in python_sell_rules:
                    signal = rule.generate_signal(market_data, temp_positions)
                    if signal == TradingSignalEnum.SELL:
                        sell_triggered = True
                        triggered_rule_name = rule_config.get("name", "Python Rule")
                        break

                # Check simple rules if no Python rule triggered
                if not sell_triggered:
                    for rule_config in simple_sell_rules:
                        change_type = rule_config.get("changeType", "")
                        threshold = rule_config.get("changePercent", 2)

                        if change_type == "price_increase" and position_pnl_pct >= threshold:
                            sell_triggered = True
                            triggered_rule_name = rule_config.get("name", "Take Profit")
                            break
                        elif change_type == "price_decrease" and position_pnl_pct <= -threshold:
                            sell_triggered = True
                            triggered_rule_name = rule_config.get("name", "Stop Loss")
                            break

                if sell_triggered:
                    revenue = current_price * pos["quantity"]
                    pnl = (current_price - pos["entry_price"]) * pos["quantity"]
                    cash += revenue
                    del held_stocks[stock]
                    trades.append(TradeRecord(
                        id=f"trade-{i}-{stock}-sell",
                        timestamp=timestamp_str,
                        stock=stock,
                        decision="SELL",
                        price=current_price,
                        quantity=pos["quantity"],
                        rule_triggered=triggered_rule_name,
                        pnl=round(pnl, 2)
                    ))

        # Record portfolio value periodically
        if i % max(1, max_length // 100) == 0:
            portfolio_value = cash
            for stk, pos in held_stocks.items():
                if stk in stock_data:
                    df = stock_data[stk]
                    idx = min(i, len(df) - 1)
                    portfolio_value += float(df.iloc[idx]["price"]) * pos["quantity"]
            portfolio_values.append(round(portfolio_value, 2))
            for stk, df in stock_data.items():
                if i < len(df):
                    timestamps.append(str(df.iloc[i]["timestamp"])[:19])
                    break

    # Close remaining positions at end
    for stock, pos in list(held_stocks.items()):
        if stock in stock_data:
            df = stock_data[stock]
            final_price = float(df.iloc[-1]["price"])
            pnl = (final_price - pos["entry_price"]) * pos["quantity"]
            cash += final_price * pos["quantity"]
            trades.append(TradeRecord(
                id=f"trade-final-{stock}",
                timestamp=str(df.iloc[-1]["timestamp"])[:19],
                stock=stock,
                decision="SELL",
                price=final_price,
                quantity=pos["quantity"],
                rule_triggered="End of Backtest",
                pnl=round(pnl, 2)
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

    return BacktestResult(
        total_trades=len(trades),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        total_pnl=round(total_pnl, 2),
        percent_return=round(percent_return, 2),
        max_drawdown=round(max_drawdown, 2),
        trades=trades,
        portfolio_values=portfolio_values,
        timestamps=timestamps
    )
