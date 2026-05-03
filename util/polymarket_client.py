"""Read-only Polymarket data access.

This module intentionally owns API shape and HTTP details so backtest logic can
operate on normalized dataframes instead of Polymarket-specific payloads.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / "polymarket.env"


class PolymarketClientError(RuntimeError):
    """Raised when Polymarket data cannot be fetched or normalized."""


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

    def l2_headers(
        self,
        method: str,
        request_path: str,
        body: Any = None,
        timestamp: int | None = None,
    ) -> dict[str, str]:
        """Create Polymarket L2 auth headers for authenticated CLOB requests."""
        if not self.has_l2_credentials():
            raise PolymarketClientError(
                "Missing L2 credentials. Set POLYMARKET_ADDRESS, "
                "POLYMARKET_API_KEY, POLYMARKET_API_SECRET, and "
                "POLYMARKET_API_PASSPHRASE in polymarket.env."
            )

        ts = int(timestamp or time.time())
        signature = _build_hmac_signature(
            secret=str(self.api_secret),
            timestamp=ts,
            method=method,
            request_path=request_path,
            body=body,
        )
        return {
            "POLY_ADDRESS": str(self.address),
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": str(ts),
            "POLY_API_KEY": str(self.api_key),
            "POLY_PASSPHRASE": str(self.api_passphrase),
        }


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
        env_path: str | Path | None = DEFAULT_ENV_PATH,
        credentials: PolymarketCredentials | None = None,
        authenticate_clob_reads: bool = False,
    ) -> None:
        self.gamma_api_url = gamma_api_url.rstrip("/")
        self.clob_api_url = clob_api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.credentials = credentials or PolymarketCredentials.from_env_file(env_path)
        self.authenticate_clob_reads = authenticate_clob_reads

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

        payload = self._get_json(
            f"{self.clob_api_url}/prices-history",
            params=params,
            authenticated=self.authenticate_clob_reads,
        )
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
        interval: str | None = "all",
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

    def get_both_outcomes_price_history(
        self,
        market_slug: str,
        start: datetime | str | int | float | None = None,
        end: datetime | str | int | float | None = None,
        interval: str | None = None,
        fidelity: int | None = 1,
    ) -> pd.DataFrame:
        """Fetch price history for both Yes and No outcomes in a single dataframe.
        
        Returns:
            DataFrame with columns: timestamp, price, token_id, outcome.
            The 'outcome' column contains 1 for "Yes" and 0 for "No".
        """
        dfs = []
        for outcome_name, outcome_value in [("Yes", 1), ("No", 0)]:
            market, token, history = self.get_outcome_price_history(
                market_slug=market_slug,
                outcome=outcome_name,
                start=start,
                end=end,
                interval=interval,
                fidelity=fidelity,
            )
            history["outcome"] = outcome_value
            dfs.append(history)
        
        combined = pd.concat(dfs, ignore_index=True)
        return combined.sort_values("timestamp").reset_index(drop=True)

    def _get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        headers = {
            "Accept": "application/json",
            "User-Agent": "SystematicTrader/0.1",
        }
        if authenticated:
            headers.update(self.credentials.l2_headers("GET", self._request_path(url, query)))

        request = Request(
            f"{url}{query}",
            headers=headers,
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

    def _post_json(
        self,
        url: str,
        body: dict[str, Any] | list[Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        serialized_body = json.dumps(body or {}, separators=(",", ":"))
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SystematicTrader/0.1",
        }
        if authenticated:
            headers.update(
                self.credentials.l2_headers(
                    "POST",
                    self._request_path(url),
                    body=serialized_body,
                )
            )

        request = Request(
            url,
            data=serialized_body.encode("utf-8"),
            headers=headers,
            method="POST",
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

    @staticmethod
    def _request_path(url: str, query: str = "") -> str:
        marker = "://"
        if marker in url:
            path_start = url.find("/", url.find(marker) + len(marker))
            path = url[path_start:] if path_start >= 0 else "/"
        else:
            path = url
        return f"{path}{query}"


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


def _build_hmac_signature(
    secret: str,
    timestamp: int,
    method: str,
    request_path: str,
    body: Any = None,
) -> str:
    try:
        decoded_secret = base64.urlsafe_b64decode(secret)
    except Exception as exc:
        raise PolymarketClientError(
            "POLYMARKET_API_SECRET must be the base64-encoded API secret from Polymarket."
        ) from exc

    message = f"{timestamp}{method}{request_path}"
    if body:
        message += str(body).replace("'", '"')

    digest = hmac.new(decoded_secret, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")
