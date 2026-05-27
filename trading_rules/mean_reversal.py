import pandas as pd

from trading_rules.trading_rule import TradingRule
from trading_rules.timeframes import TimeframesEnum
from trading_rules.market_data import MarketData, PRICE
from trading_rules.position_data import Positions
from trading_rules.signals import TradingSignalEnum, TradingSignal
class HoldingTimeEnumMinutes:
    SIXTY_MINUTES = 60
    ONE_DAY = 1440
    TWO_DAYS = 2880
    ONE_WEEK = 10080


class MeanReversal(TradingRule):
    DESCRIPTION = """Z-Score based Mean Reversion trading rule.
    
    Trading rule that identifies mean reversion opportunities using z-scores to measure 
    price deviations from the statistical mean. A z-score measures how many standard deviations 
    the current price is from the mean:
    
        z-score = (current_price - mean) / standard_deviation
    
    Entry Signals:
    - BUY when z-score <= entry_z_threshold_buy (price is significantly below mean)
    - SELL when z-score >= entry_z_threshold_sell (price is significantly above mean)
    
    Exit strategy is handled by a separate exit rule.
    
    Parameters:
    - lookback_window: Number of periods for mean and std calculation
    - entry_z_threshold_buy: Z-score level below which to generate BUY signal (typically negative, e.g., -2.0)
    - entry_z_threshold_sell: Z-score level above which to generate SELL signal (typically positive, e.g., 2.0)
    """
    
    def __init__(self, lookback_window=20, entry_z_threshold_entry=2.0, exit_z_threshold=0.5):
        """
        Initialize the Z-Score Mean Reversion trading rule.
        
        Args:
            lookback_window: Number of periods for mean & std deviation calculation (default: 20)
            entry_z_threshold_buy: Z-score threshold for BUY signal (default: -2.0)
                                  Typically negative; lower = more extreme, fewer trades
            entry_z_threshold_sell: Z-score threshold for SELL signal (default: 2.0)
                                   Typically positive; higher = more extreme, fewer trades
        """
        self.lookback_window = lookback_window
        self.entry_z_threshold = entry_z_threshold_entry
        self.exit_z_threshold = exit_z_threshold

    def generate_signal_buy_at_entry_sell_after_time(self,
                                                     symbol: str,
                                                     market_data: MarketData,
                                                     positions_data: Positions,
                                                     holding_time=HoldingTimeEnumMinutes.ONE_DAY) -> TradingSignal:
        """
        Generate entry signals based on X-day rolling minimum (paper strategy).

        Entry: BUY when current price <= minimum of lookback window (new period low).
        Exit: SELL after holding_time minutes have elapsed.
        """
        if market_data.df.empty:
            return TradingSignalEnum.HOLD

        # Check we are looking at a window with at least "lookback window" days
        # worth of data.
        days_of_data = market_data.df.index.normalize().nunique()
        if days_of_data < self.lookback_window:
            return TradingSignalEnum.HOLD

        current_price = market_data.get_latest_price()
        current_timestamp = market_data.get_latest_timestamp()

        min_price = market_data.df[PRICE].iloc[:-1].min()


        if positions_data.are_we_holding_positions():
            holding_time_minutes = positions_data.get_holding_time_minutes(symbol=symbol,
                                                                           current_time_timestamp=current_timestamp)
            print(holding_time_minutes)
            if holding_time_minutes >= holding_time:
                return TradingSignalEnum.SELL
        else:
            if current_price <= min_price:
                return TradingSignalEnum.BUY

        return TradingSignalEnum.HOLD         
        

    def generate_signal_z_score(self, market_data: MarketData, positions_data: Positions) -> TradingSignal:
        """
        Generate entry signals based on z-score deviation from mean.
        
        Returns:
            BUY if z-score <= entry_z_threshold_buy
            SELL if z-score >= entry_z_threshold_sell
            NONE otherwise
        """
        current_price = market_data.get_latest_price()
        mean = market_data.get_mean(self.lookback_window)
        std = market_data.get_std(self.lookback_window)
        
        # Handle edge case where std is 0 or NaN (all prices identical or insufficient data)
        if std == 0 or std != std:  # std != std checks for NaN
            return TradingSignalEnum.NONE
        
        z_score = self.calculate_z_score(current_price, mean, std)

        if positions_data.are_we_holding_positions():
            
            if z_score <= self.exit_z_threshold:
                return TradingSignalEnum.SELL
            else:
                return TradingSignalEnum.HOLD
        else:

            if z_score <= -self.entry_z_threshold:
                return TradingSignalEnum.BUY
            else:
                return TradingSignalEnum.HOLD

    def calculate_z_score(self, price: float, mean: float, std: float) -> float:
        """
        Calculate z-score: (price - mean) / std
        
        Args:
            price: Current price
            mean: Mean price over lookback window
            std: Standard deviation of price over lookback window
        
        Returns:
            Z-score value. Positive values indicate price above mean, negative below.
        """
        return (price - mean) / std if std != 0 else 0.0