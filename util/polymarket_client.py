"""Read-only Polymarket data access.

This module intentionally owns API shape and HTTP details so backtest logic can
operate on normalized dataframes instead of Polymarket-specific payloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
DEFAULT_TIMEOUT_SECONDS = 30


class PolymarketClientError(RuntimeError):
    """Raised when Polymarket data cannot be fetched or normalized."""


@dataclass(frozen=True)
class PolymarketToken:
    """A tradable outcome token on a Polymarket market."""

    token_id: str
    outcome: str


@dataclass(frozen=True)
class PolymarketMarket:
    """Market metadata needed by the backtester."""

    id: str | None
    slug: str | None
    question: str | None
    condition_id: str | None
    tokens: tuple[PolymarketToken, ...]
    raw: dict[str, Any]

    def get_token(self, outcome: str) -> PolymarketToken:
        requested = outcome.casefold()
        for token in self.tokens:
            if token.outcome.casefold() == requested:
                return token
        available = ", ".join(token.outcome for token in self.tokens)
        raise PolymarketClientError(
            f"Outcome {outcome!r} not found. Available outcomes: {available}"
        )


class PolymarketClient:
    """Small read-only client for Polymarket public APIs."""

    def __init__(
        self,
        gamma_api_url: str = GAMMA_API_URL,
        clob_api_url: str = CLOB_API_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.gamma_api_url = gamma_api_url.rstrip("/")
        self.clob_api_url = clob_api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_market_by_slug(self, slug: str) -> PolymarketMarket:
        """Fetch market metadata from Gamma by URL slug."""
        payload = self._get_json(f"{self.gamma_api_url}/markets/slug/{slug}")
        if not isinstance(payload, dict):
            raise PolymarketClientError(f"Unexpected market payload for slug {slug!r}")
        return self._normalize_market(payload)

    def get_price_history(
        self,
        token_id: str,
        start: datetime | str | int | float | None = None,
        end: datetime | str | int | float | None = None,
        interval: str | None = None,
        fidelity: int | None = 1,
    ) -> pd.DataFrame:
        """Fetch and normalize CLOB price history for an outcome token.

        Returns a dataframe with `timestamp`, `price`, and `token_id` columns.
        `timestamp` is timezone-aware UTC and `price` is a float between 0 and 1.
        """
        params: dict[str, str | int] = {"market": token_id}
        start_ts = self._to_unix_seconds(start)
        end_ts = self._to_unix_seconds(end)

        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts
        if interval:
            params["interval"] = interval
        if fidelity is not None:
            params["fidelity"] = fidelity

        payload = self._get_json(f"{self.clob_api_url}/prices-history", params=params)
        history = payload.get("history") if isinstance(payload, dict) else None
        if not isinstance(history, list):
            raise PolymarketClientError("Unexpected price history response")

        df = pd.DataFrame(history)
        if df.empty:
            return pd.DataFrame(columns=["timestamp", "price", "token_id"])

        missing_columns = {"t", "p"} - set(df.columns)
        if missing_columns:
            raise PolymarketClientError(f"Price history missing columns: {missing_columns}")

        df = df.rename(columns={"t": "timestamp", "p": "price"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["token_id"] = token_id
        df = df.dropna(subset=["timestamp", "price"])
        df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
        return df[["timestamp", "price", "token_id"]]

    def get_outcome_price_history(
        self,
        market_slug: str,
        outcome: str = "Yes",
        start: datetime | str | int | float | None = None,
        end: datetime | str | int | float | None = None,
        interval: str | None = None,
        fidelity: int | None = 1,
    ) -> tuple[PolymarketMarket, PolymarketToken, pd.DataFrame]:
        """Resolve an outcome token for a market slug and fetch its history."""
        market = self.get_market_by_slug(market_slug)
        token = market.get_token(outcome)
        history = self.get_price_history(
            token.token_id,
            start=start,
            end=end,
            interval=interval,
            fidelity=fidelity,
        )
        return market, token, history

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{url}{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "SystematicTrader/0.1",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise PolymarketClientError(f"Polymarket HTTP {exc.code}: {details}") from exc
        except (URLError, TimeoutError) as exc:
            raise PolymarketClientError(f"Could not reach Polymarket: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise PolymarketClientError("Polymarket returned invalid JSON") from exc

    def _normalize_market(self, payload: dict[str, Any]) -> PolymarketMarket:
        outcomes = self._decode_jsonish_list(payload.get("outcomes"))
        token_ids = self._decode_jsonish_list(payload.get("clobTokenIds"))

        if len(outcomes) != len(token_ids):
            raise PolymarketClientError(
                "Market outcomes and clobTokenIds have different lengths"
            )
        if not token_ids:
            raise PolymarketClientError("Market has no CLOB token ids")

        tokens = tuple(
            PolymarketToken(token_id=str(token_id), outcome=str(outcome))
            for outcome, token_id in zip(outcomes, token_ids)
        )

        return PolymarketMarket(
            id=self._optional_str(payload.get("id")),
            slug=self._optional_str(payload.get("slug")),
            question=self._optional_str(payload.get("question")),
            condition_id=self._optional_str(
                payload.get("conditionId") or payload.get("condition_id")
            ),
            tokens=tokens,
            raw=payload,
        )

    @staticmethod
    def _decode_jsonish_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise PolymarketClientError(f"Could not decode list field: {value}") from exc
            if isinstance(decoded, list):
                return decoded
        raise PolymarketClientError(f"Expected list-like field, got {type(value).__name__}")

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
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
