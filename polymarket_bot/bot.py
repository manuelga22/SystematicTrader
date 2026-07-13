"""Event loop: polymarket_socket -> rules -> decide -> execute.

The socket pushes closed bars onto an internal queue via ``on_bar_close``.
The loop consumes them and, per asset:

- flat      -> run the entry rule; on signal, market-buy a fixed USD size
- in market -> run the exit rule;  on signal, market-sell the whole position

Bars normally close when the first tick of the next window arrives; in quiet
markets the loop force-closes bars whose window has elapsed so rules keep
firing.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Protocol
from util.log_service import LogService

from polymarket_account import Position
from polymarket_socket import PolymarketSocket
from price_book import Bar, PriceBook

LOGGER_NAME = "BOT"

log = LogService(name=LOGGER_NAME)

# entry(book, asset_id) -> True to open a position
EntryRule = Callable[[PriceBook, str], bool]
# exit(book, asset_id, position) -> True to close the position
ExitRule = Callable[[PriceBook, str, Position], bool]


class Execution(Protocol):
    def market_buy(self, asset_id: str, usd_amount: float) -> dict | None: ...
    def market_sell(self, asset_id: str, shares: float) -> dict | None: ...


class Account(Protocol):
    def position(self, asset_id: str) -> Position | None: ...


class Bot:
    def __init__(self, asset_ids: list[str], price_book: PriceBook, account: Account, execution: Execution,
        entry_rule: EntryRule, exit_rule: ExitRule, order_size_usd: float) -> None:

        self.asset_ids = asset_ids
        self.book = price_book
        self.account = account
        self.execution = execution
        self.entry_rule = entry_rule
        self.exit_rule = exit_rule
        self.order_size_usd = order_size_usd
        self._queue: asyncio.Queue[tuple[str, Bar]] = asyncio.Queue()
        self.socket = PolymarketSocket(asset_ids, price_book, self.on_bar_close)

    async def on_bar_close(self, asset_id: str, bar: Bar) -> None:
        """Callback handed to PolymarketSocket."""
        await self._queue.put((asset_id, bar))

    async def run(self) -> None:
        socket_task = asyncio.create_task(self.socket.run())
        log.info(
            "bot running: %d asset(s), %ds bars, $%.2f per entry",
            len(self.asset_ids), self.book.bar_seconds, self.order_size_usd,
        )
        try:
            while True:
                try:
                    asset_id, bar = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    self._flush_stale_bars()
                    continue
                self._on_bar(asset_id, bar)
        finally:
            socket_task.cancel()

    def _flush_stale_bars(self) -> None:
        now = time.time()
        for asset_id in self.asset_ids:
            bar = self.book.force_close(asset_id, now)
            if bar is not None:
                self._on_bar(asset_id, bar)

    def _on_bar(self, asset_id: str, bar: Bar) -> None:
        log.debug(
            "bar closed %s: o=%.4f h=%.4f l=%.4f c=%.4f (%d ticks)",
            asset_id[:16], bar.open, bar.high, bar.low, bar.close, bar.n_ticks,
        )
        try:
            self._decide(asset_id)
        except Exception:
            log.exception("rule evaluation failed for %s", asset_id)

    def _decide(self, asset_id: str) -> None:
        position = self.account.position(asset_id)
        if position is None or not position.is_open:
            if self.entry_rule(self.book, asset_id):
                log.info("entry signal on %s", asset_id[:16])
                self.execution.market_buy(asset_id, self.order_size_usd)
        else:
            if self.exit_rule(self.book, asset_id, position):
                log.info("exit signal on %s", asset_id[:16])
                self.execution.market_sell(asset_id, position.shares)
