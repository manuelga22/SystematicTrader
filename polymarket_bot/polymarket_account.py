"""Read-only view of a live Polymarket account: positions, orders, balances.

Positions come from the public data API (keyed by wallet address); open
orders and the USDC balance come from the authenticated CLOB client. Nothing
in this module mutates account state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

DATA_API = "https://data-api.polymarket.com"


@dataclass
class Position:
    asset_id: str
    shares: float
    avg_price: float

    @property
    def is_open(self) -> bool:
        return self.shares > 0


class PolymarketAccount:
    def __init__(self, clob_client, address: str) -> None:
        self.client = clob_client
        self.address = address

    def positions(self) -> dict[str, Position]:
        resp = requests.get(
            f"{DATA_API}/positions", params={"user": self.address}, timeout=10
        )
        resp.raise_for_status()
        out: dict[str, Position] = {}
        for item in resp.json():
            asset_id = str(item.get("asset", ""))
            size = float(item.get("size", 0) or 0)
            if not asset_id or size <= 0:
                continue
            out[asset_id] = Position(
                asset_id=asset_id,
                shares=size,
                avg_price=float(item.get("avgPrice", 0) or 0),
            )
        return out

    def position(self, asset_id: str) -> Position | None:
        return self.positions().get(asset_id)

    def open_orders(self, asset_id: str | None = None) -> list[dict]:
        from py_clob_client.clob_types import OpenOrderParams

        params = OpenOrderParams(asset_id=asset_id) if asset_id else OpenOrderParams()
        return self.client.get_orders(params) or []

    def usdc_balance(self) -> float:
        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams

        res = self.client.get_balance_allowance(
            BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        return float(res["balance"]) / 1e6  # USDC has 6 decimals
