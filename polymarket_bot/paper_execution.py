"""Paper trading: fake order execution with realistic slippage.

Implements the same execution interface as OrderExecution (market_buy /
market_sell / cancel_all) plus the read-only account interface of
PolymarketAccount (position / positions / open_orders / usdc_balance), so in
paper mode a single instance serves as both.

Fill model: buys fill at the live ask, sells at the live bid (falling back to
the last known price when no quote is available), then an additional
``slippage_bps`` of adverse price impact is applied. Fills are clamped to
Polymarket's valid (0, 1) price range.
"""

from __future__ import annotations

import logging
import time

from order_execution import CooldownGuard
from polymarket_account import Position
from price_book import PriceBook

log = logging.getLogger(__name__)

MIN_PRICE = 0.001
MAX_PRICE = 0.999


class PaperExecution:
    def __init__(self, price_book: PriceBook, starting_cash: float = 1_000.0, 
                 slippage_bps: float = 20.0, cooldown_s: float = 60.0) -> None:
        self.book = price_book
        self.cash = starting_cash
        self.slippage = slippage_bps / 10_000.0
        self.guard = CooldownGuard(cooldown_s)
        self._positions: dict[str, Position] = {}
        self.trades: list[dict] = []

    # -- execution interface -------------------------------------------------

    def market_buy(self, asset_id: str, usd_amount: float) -> dict | None:
        if usd_amount <= 0:
            return None
        if not self.guard.ready(asset_id):
            log.info("paper cooldown active for %s, skipping buy", asset_id)
            return None
        fill = self._fill_price(asset_id, buying=True)
        if fill is None:
            log.warning("no price for %s yet, cannot fill buy", asset_id)
            return None
        if usd_amount > self.cash:
            log.warning("insufficient paper cash (%.2f < %.2f)", self.cash, usd_amount)
            return None
        self.guard.stamp(asset_id)

        shares = usd_amount / fill
        self.cash -= usd_amount
        pos = self._positions.get(asset_id)
        if pos is None or pos.shares <= 0:
            self._positions[asset_id] = Position(asset_id, shares, fill)
        else:
            total = pos.shares + shares
            pos.avg_price = (pos.avg_price * pos.shares + fill * shares) / total
            pos.shares = total
        return self._record("BUY", asset_id, shares, fill)

    def market_sell(self, asset_id: str, shares: float) -> dict | None:
        pos = self._positions.get(asset_id)
        if pos is None or pos.shares <= 0:
            log.warning("no paper position in %s to sell", asset_id)
            return None
        if not self.guard.ready(asset_id):
            log.info("paper cooldown active for %s, skipping sell", asset_id)
            return None
        fill = self._fill_price(asset_id, buying=False)
        if fill is None:
            log.warning("no price for %s yet, cannot fill sell", asset_id)
            return None
        self.guard.stamp(asset_id)

        shares = min(shares, pos.shares)
        self.cash += shares * fill
        pos.shares -= shares
        if pos.shares <= 1e-9:
            del self._positions[asset_id]
        return self._record("SELL", asset_id, shares, fill)


    def get_positions(self) -> dict[str, Position]:
        return self._positions

    def get_position(self, asset_id: str) -> Position | None:
        return self._positions.get(asset_id)
    
    def get_balance(self) -> float:
        return self.cash

    def get_equity(self) -> float:
        """Cash plus positions marked at the last known price."""
        total = self.cash
        for asset_id, pos in self._positions.items():
            mark = self.book.last_price(asset_id) or pos.avg_price
            total += pos.shares * mark
        return total


    def _fill_price(self, asset_id: str, buying: bool) -> float | None:
        quote = self.book.quote(asset_id)
        ref = (quote.ask if buying else quote.bid) or self.book.last_price(asset_id)
        if ref is None:
            return None
        fill = ref * (1 + self.slippage) if buying else ref * (1 - self.slippage)
        return min(max(fill, MIN_PRICE), MAX_PRICE)

    def _record(self, action: str, asset_id: str, shares: float, fill: float) -> dict:
        trade = {
            "ts": time.time(),
            "action": action,
            "asset_id": asset_id,
            "shares": round(shares, 6),
            "price": round(fill, 6),
            "cash_after": round(self.cash, 2),
        }
        self.trades.append(trade)
        log.info(
            "PAPER %s %s: %.4f shares @ %.4f | cash=%.2f equity=%.2f pnl=%.2f",
            action, asset_id[:16], shares, fill, self.cash, self.equity(), self.realized_pnl,
        )
        return trade
