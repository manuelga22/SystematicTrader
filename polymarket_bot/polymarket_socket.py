"""Websocket connection to the Polymarket CLOB market channel.

Subscribes to the given asset (token) ids and feeds every price event into
the PriceBook:

- ``book`` events (full snapshots) yield the best bid/ask; the mid-price
  becomes a tick.
- ``price_change`` events carry ``best_bid``/``best_ask`` per changed asset;
  the updated mid becomes a tick.
- ``last_trade_price`` events emit a trade-price tick.

Whenever a tick closes a bar, ``on_bar_close(asset_id, bar)`` is awaited so
the bot can run its rules.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Awaitable, Callable

import websockets

from price_book import Bar, PriceBook

log = logging.getLogger(__name__)

MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

BarCallback = Callable[[str, Bar], Awaitable[None]]


class PolymarketSocket:
    def __init__(
        self,
        asset_ids: list[str],
        price_book: PriceBook,
        on_bar_close: BarCallback,
        url: str = MARKET_WS_URL,
        ping_interval_s: float = 10.0,
        reconnect_delay_s: float = 2.0,
        max_reconnect_delay_s: float = 60.0,
    ) -> None:
        if not asset_ids:
            raise ValueError("asset_ids must not be empty")
        self.asset_ids = set(asset_ids)
        self.book = price_book
        self.on_bar_close = on_bar_close
        self.url = url
        self.ping_interval_s = ping_interval_s
        self.reconnect_delay_s = reconnect_delay_s
        self.max_reconnect_delay_s = max_reconnect_delay_s

    async def run(self) -> None:
        """Connect and process messages forever, reconnecting with backoff."""
        delay = self.reconnect_delay_s
        while True:
            try:
                async with websockets.connect(self.url, max_size=2**22) as ws:
                    log.info("websocket connected, subscribing to %d asset(s)", len(self.asset_ids))
                    await ws.send(json.dumps({"type": "market", "assets_ids": sorted(self.asset_ids)}))
                    delay = self.reconnect_delay_s
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    try:
                        async for raw in ws:
                            await self._handle_raw(raw)
                    finally:
                        ping_task.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("websocket error (%s), reconnecting in %.0fs", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.max_reconnect_delay_s)

    async def _ping_loop(self, ws) -> None:
        # The subscriptions endpoint drops idle connections; keep it warm.
        while True:
            await asyncio.sleep(self.ping_interval_s)
            await ws.send("PING")

    async def _handle_raw(self, raw: str | bytes) -> None:
        if isinstance(raw, bytes):
            raw = raw.decode()
        if raw == "PONG":
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            log.debug("ignoring non-JSON message: %.80s", raw)
            return
        events = payload if isinstance(payload, list) else [payload]
        for event in events:
            if isinstance(event, dict):
                await self._handle_event(event)

    async def _handle_event(self, event: dict) -> None:
        event_type = event.get("event_type")
        ts = _event_ts(event)

        if event_type == "book":
            asset_id = event.get("asset_id")
            if asset_id not in self.asset_ids:
                return
            bids = [float(l["price"]) for l in event.get("bids", [])]
            asks = [float(l["price"]) for l in event.get("asks", [])]
            bid = max(bids) if bids else None
            ask = min(asks) if asks else None
            await self._quote_tick(asset_id, bid, ask, ts)
        elif event_type == "price_change":
            for change in event.get("price_changes", []):
                asset_id = change.get("asset_id")
                if asset_id not in self.asset_ids:
                    continue
                bid = _opt_float(change.get("best_bid"))
                ask = _opt_float(change.get("best_ask"))
                await self._quote_tick(asset_id, bid, ask, ts)
        elif event_type == "last_trade_price":
            asset_id = event.get("asset_id")
            if asset_id not in self.asset_ids:
                return
            await self._tick(asset_id, float(event["price"]), ts)

    async def _quote_tick(self, asset_id: str, bid: float | None, ask: float | None, ts: float) -> None:
        self.book.set_quote(asset_id, bid, ask)
        if bid is not None and ask is not None:
            await self._tick(asset_id, (bid + ask) / 2.0, ts)

    async def _tick(self, asset_id: str, price: float, ts: float) -> None:
        closed = self.book.update(asset_id, price, ts)
        if closed is not None:
            await self.on_bar_close(asset_id, closed)


def _opt_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_ts(event: dict) -> float:
    raw = event.get("timestamp")
    if raw is not None:
        try:
            ts = float(raw)
            return ts / 1000.0 if ts > 1e12 else ts  # ms vs s
        except (TypeError, ValueError):
            pass
    return time.time()
