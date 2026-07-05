"""In-memory price history: bounded per-asset bar storage.

The book ingests raw ticks (trade prices or book mid-prices) and aggregates
them into fixed-interval OHLC bars. Only the most recent ``max_bars`` bars
are kept per asset (backed by a deque with ``maxlen``).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Bar:
    ts: float  # bucket start, unix seconds
    open: float
    high: float
    low: float
    close: float
    n_ticks: int = 1

    def update(self, price: float) -> None:
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.n_ticks += 1


@dataclass
class Quote:
    bid: float | None = None
    ask: float | None = None

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2.0


@dataclass
class _AssetHistory:
    bars: deque[Bar]
    current: Bar | None = None
    quote: Quote = field(default_factory=Quote)


class PriceBook:
    """Bounded rolling window of bars per asset id."""

    def __init__(self, max_bars: int = 500, bar_seconds: int = 60) -> None:
        if max_bars < 1:
            raise ValueError("max_bars must be >= 1")
        if bar_seconds < 1:
            raise ValueError("bar_seconds must be >= 1")
        self.max_bars = max_bars
        self.bar_seconds = bar_seconds
        self._assets: dict[str, _AssetHistory] = {}

    def _history(self, asset_id: str) -> _AssetHistory:
        hist = self._assets.get(asset_id)
        if hist is None:
            hist = _AssetHistory(bars=deque(maxlen=self.max_bars))
            self._assets[asset_id] = hist
        return hist

    def update(self, asset_id: str, price: float, ts: float) -> Bar | None:
        """Ingest one tick. Returns the just-closed bar when the tick opens a
        new bucket, otherwise None. Bars close lazily: a bar is considered
        closed when the first tick of a later bucket arrives."""
        hist = self._history(asset_id)
        bucket = int(ts // self.bar_seconds) * self.bar_seconds

        if hist.current is None:
            hist.current = Bar(ts=bucket, open=price, high=price, low=price, close=price)
            return None

        if bucket <= hist.current.ts:
            hist.current.update(price)
            return None

        closed = hist.current
        hist.bars.append(closed)
        hist.current = Bar(ts=bucket, open=price, high=price, low=price, close=price)
        return closed

    def force_close(self, asset_id: str, now: float) -> Bar | None:
        """Close the forming bar if its window has fully elapsed, even though
        no new tick has arrived. Returns the closed bar, or None if there is
        no forming bar or its window is still open."""
        hist = self._history(asset_id)
        cur = hist.current
        if cur is None or now < cur.ts + self.bar_seconds:
            return None
        hist.bars.append(cur)
        hist.current = None
        return cur

    def set_quote(self, asset_id: str, bid: float | None, ask: float | None) -> None:
        self._history(asset_id).quote = Quote(bid=bid, ask=ask)

    def quote(self, asset_id: str) -> Quote:
        return self._history(asset_id).quote

    def bars(self, asset_id: str) -> list[Bar]:
        """Closed bars, oldest first."""
        return list(self._history(asset_id).bars)

    def closes(self, asset_id: str) -> list[float]:
        return [b.close for b in self._history(asset_id).bars]

    def last_price(self, asset_id: str) -> float | None:
        """Most recent traded/mid price seen (including the forming bar)."""
        hist = self._history(asset_id)
        if hist.current is not None:
            return hist.current.close
        if hist.bars:
            return hist.bars[-1].close
        return None

    def __len__(self) -> int:
        return len(self._assets)
