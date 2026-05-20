import pandas as pd


class TickDataIntervalEnum:
    """Enumeration of tick data intervals for Polymarket price history."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    TEN_MINUTES = "10m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1m"
    ONE_YEAR = "1y"

def parse_timestamp(df: pd.DataFrame, timestamp_column: str = "timestamp") -> pd.Series:
    """Convert timestamp series to datetime and set as index.
    This function also adds 5 columns for year, month, day, hour, and minute."""

    df[timestamp_column] = pd.to_datetime(df[timestamp_column], unit="ms")
    df["year"] = df[timestamp_column].dt.year
    df["month"] = df[timestamp_column].dt.month
    df["day"] = df[timestamp_column].dt.day
    df["hour"] = df[timestamp_column].dt.hour
    df["minute"] = df[timestamp_column].dt.minute
    
    return df
    