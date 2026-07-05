"""Live order execution on the Polymarket CLOB.

Order construction and EIP-712 signing are delegated to py-clob-client; this
module wraps it with market-style (fill-or-kill) buy/sell helpers and a
per-asset cooldown guard so the bot cannot fire orders faster than intended.

py-clob-client is imported lazily inside methods so that paper mode (which
imports CooldownGuard from here) works without the package installed.
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)


class CooldownGuard:
    """Refuses actions on a key more often than once per ``cooldown_s``."""

    def __init__(self, cooldown_s: float) -> None:
        self.cooldown_s = cooldown_s
        self._last: dict[str, float] = {}

    def ready(self, key: str) -> bool:
        last = self._last.get(key)
        return last is None or (time.monotonic() - last) >= self.cooldown_s

    def stamp(self, key: str) -> None:
        self._last[key] = time.monotonic()


class OrderExecution:
    def __init__(self, clob_client, cooldown_s: float = 60.0) -> None:
        self.client = clob_client
        self.guard = CooldownGuard(cooldown_s)

    def market_buy(self, asset_id: str, usd_amount: float) -> dict | None:
        """Buy ``usd_amount`` USDC worth of the token, fill-or-kill."""
        from py_clob_client.order_builder.constants import BUY

        return self._market_order(asset_id, BUY, usd_amount)

    def market_sell(self, asset_id: str, shares: float) -> dict | None:
        """Sell ``shares`` tokens, fill-or-kill."""
        from py_clob_client.order_builder.constants import SELL

        return self._market_order(asset_id, SELL, shares)

    def _market_order(self, asset_id: str, side: str, amount: float) -> dict | None:
        from py_clob_client.clob_types import MarketOrderArgs, OrderType

        if amount <= 0:
            log.warning("skipping %s on %s: non-positive amount %s", side, asset_id, amount)
            return None
        if not self.guard.ready(asset_id):
            log.info("cooldown active for %s, skipping %s", asset_id, side)
            return None
        self.guard.stamp(asset_id)  # stamp on attempt so failures don't retry-spam

        try:
            signed = self.client.create_market_order(
                MarketOrderArgs(token_id=asset_id, amount=amount, side=side)
            )
            resp = self.client.post_order(signed, orderType=OrderType.FOK)
        except Exception:
            log.exception("order failed: %s %s amount=%s", side, asset_id, amount)
            return None
        log.info("posted %s %s amount=%s -> %s", side, asset_id, amount, resp)
        return resp

    def cancel(self, order_id: str) -> dict | None:
        try:
            return self.client.cancel(order_id)
        except Exception:
            log.exception("cancel failed for order %s", order_id)
            return None

    def cancel_all(self) -> dict | None:
        try:
            return self.client.cancel_all()
        except Exception:
            log.exception("cancel_all failed")
            return None
