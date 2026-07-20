"""Read-only Polymarket data access using pmxt library.

This module uses pmxt for market data access so backtest logic can
operate on normalized dataframes instead of Polymarket-specific payloads.
"""

from __future__ import annotations

import pmxt
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pmxt import Polymarket as PMXTClient
from util.data_processor import TickDataIntervalEnum

DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / "polymarket.env"

class PolymarketClientError(RuntimeError):
    """Raised when Polymarket data cannot be fetched or normalized."""


# Convert interval into seconds
interval_seconds_map = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

class VolumeDataEnum:
    """Enumeration of volume data intervals for Polymarket price history."""
    ONE_THOUSAND = "1000"
    TEN_THOUSAND = "10000"
    ONE_HUNDRED_THOUSAND = "100000"
    ONE_MILLION = "1000000"

@dataclass(frozen=True)
class PolymarketCredentials:
    """Polymarket credentials loaded from environment variables."""

    address: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_passphrase: str | None = None
    private_key: str | None = None

    @classmethod
    def from_env_file(cls, env_path: str | Path | None = DEFAULT_ENV_PATH) -> "PolymarketCredentials":
        values = _load_env_file(env_path)
        values.update({key: value for key, value in os.environ.items() if value})

        return cls(
            address=values.get("POLYMARKET_ADDRESS") or values.get("POLY_ADDRESS"),
            api_key=values.get("POLYMARKET_API_KEY") or values.get("POLY_API_KEY"),
            api_secret=values.get("POLYMARKET_API_SECRET"),
            api_passphrase=(
                values.get("POLYMARKET_API_PASSPHRASE")
                or values.get("POLYMARKET_PASSPHRASE")
                or values.get("POLY_PASSPHRASE")
            ),
            private_key=values.get("POLYMARKET_PRIVATE_KEY") or values.get("PRIVATE_KEY"),
        )

    def has_l2_credentials(self) -> bool:
        return all([self.address, self.api_key, self.api_secret, self.api_passphrase])


class PolymarketAPIClient:
    """Small read-only client for Polymarket using pmxt library."""

    def __init__(self, credentials: PolymarketCredentials = None):
        self.credentials = credentials or PolymarketCredentials.from_env_file(DEFAULT_ENV_PATH)
        self.pmxt_client =  pmxt.Polymarket()

    def get_market_by_slug(self, slug: str):
        """Fetch market metadata by URL slug using pmxt."""
        try:
            market_data = self.pmxt_client.fetch_markets(slug=slug)
            return market_data
        except Exception as exc:
            raise PolymarketClientError(f"Failed to fetch market {slug!r}: {exc}") from exc

    def get_price_history_by_outcome(self, market_slug: str, outcome: str = "Yes",
                                     start_ts: datetime = None, end_ts: datetime = None,
                                     fidelity: int = 1, interval: TickDataIntervalEnum = TickDataIntervalEnum.ONE_DAY) -> pd.DataFrame:
        """Resolve an outcome token for a market slug and fetch its history."""
        market = self.get_market_by_slug(market_slug)

        
        # Determine the outcome token ID based on the desired outcome label (e.g., "Yes" or "No")
        # The market response contains a label with the work "Not" in it for the "No" outcome, 
        # so we can use that to identify the correct token.
        outcomes = market[0].outcomes
        for outcome in outcomes:
            print(outcome.label)
            if "Not" not in outcome.label and desired_outcome == "Yes":
                token = outcome.outcome_id
                break
            elif "Not" in outcome.label and desired_outcome == "No":
                token = outcome.outcome_id
                break
        
        # Grab the datetime when the market resolved, so we can use that as the end time for fetching price history.
        resolved_date = market[0].resolution_date
  
        history = self._get_price_history(
            token,
            resolved_date,
            start_date=start,
            fidelity=fidelity,
            interval=interval,
        )
        return history
    
    def get_price_history_by_outcome_volume_candles(self, market_slug: str, desired_outcome: str = "Yes",
                                     start: datetime = None, end: datetime = None,
                                     fidelity: int = 1, volume_interval: TickDataIntervalEnum = VolumeDataEnum.ONE_THOUSAND) -> pd.DataFrame:
        """Resolve an outcome token for a market slug and fetch its history."""
        market = self.get_market_by_slug(market_slug)
        # Determine the outcome token ID based on the desired outcome label (e.g., "Yes" or "No")
        # The market response contains a label with the work "Not" in it for the "No" outcome, 
        # so we can use that to identify the correct token.
        outcomes = market[0].outcomes
        for outcome in outcomes:
            print(outcome.label)
            if "Not" not in outcome.label and desired_outcome == "Yes":
                token = outcome.outcome_id
                break                        
            elif "Not" in outcome.label and desired_outcome == "No":
                token = outcome.outcome_id
                break
        # Grab the datetime when the market resolved, so we can use that as the end time for fetching price history.
        resolved_date = market[0].resolution_date
        history = self._get_price_history(
            token,
            resolved_date,
            start_date=start,
            fidelity=volume_interval,
            interval=TickDataIntervalEnum.ONE_DAY,
        )
        return history


    def _get_price_history(self, token_id: str, resolved_date=None, start_date: datetime = None,
                            fidelity: int = 1, chunk_days: int = 15, interval: TickDataIntervalEnum = TickDataIntervalEnum.ONE_DAY) -> pd.DataFrame:
        """Fetch price history for an outcome token using multiple paginated requests.

        Iterates from start_date to resolved_date in chunk_days increments, concatenating results.
        Returns a dataframe with `timestamp`, `price`, and `token_id` columns.
        """
        try:
            end_dt = resolved_date
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
            if end_dt is None:
                end_dt = datetime.now(tz=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            start_dt = start_date
            if start_dt is None:
                start_dt = end_dt - timedelta(days=365)
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            chunk_size = timedelta(days=chunk_days)
            all_frames = []
            chunk_start = start_dt

            while chunk_start < end_dt:
                chunk_end = min(chunk_start + chunk_size, end_dt)

                history_data = self.pmxt_client.fetch_ohlcv(
                    outcome_id=token_id,
                    resolution=interval,
                    fidelity=fidelity,
                    start=chunk_start,
                    end=chunk_end,
                )

                if history_data:
                    all_frames.append(pd.DataFrame(history_data))

                chunk_start = chunk_end

            if not all_frames:
                return pd.DataFrame(columns=["timestamp", "price", "token_id"])

            df = pd.concat(all_frames, ignore_index=True)

            if df.empty:
                return pd.DataFrame(columns=["timestamp", "price", "token_id"])

            df["outcome_id"] = token_id
            df['timestamp_formatted'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            
            # set timestamp_formatted to be the index
            df.set_index('timestamp_formatted', inplace=True)
            
            print("requested start and end:", start_dt, end_dt)

            return df

        except PolymarketClientError:
            raise
        except Exception as exc:
            raise PolymarketClientError(f"Failed to fetch price history: {exc}")
        
    
    @staticmethod
    def _optional_str(value: Any) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _to_unix_seconds(value: datetime | str | int | float | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(parsed.timestamp())
        if isinstance(value, datetime):
            return int(value.timestamp())
        else:
            parsed = value
        
        raise PolymarketClientError(f"Cannot convert {type(value).__name__} to unix timestamp")
    
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())


def _load_env_file(env_path: str | Path | None) -> dict[str, str]:
    if env_path is None:
        return {}

    path = Path(env_path)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values
