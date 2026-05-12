import pandas as pd

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

    