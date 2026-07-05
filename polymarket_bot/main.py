"""Config, params, wiring and entry point for the Polymarket bot.

Defines the entry/exit strategies (z-score mean reversion, matching the rest
of this repo) and wires everything together for either paper or live trading:

    python main.py --mode paper --assets <token_id>[,<token_id>...]
    python main.py --mode live  --assets <token_id>

Asset ids are CLOB token ids (long decimal strings). Find them via the Gamma
API, e.g. https://gamma-api.polymarket.com/markets?slug=<market-slug>
(field ``clobTokenIds``).

Live mode reads credentials from ../polymarket.env (see repo root).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from bot import Bot, EntryRule, ExitRule
from polymarket_account import Position
from price_book import PriceBook

ROOT = Path(__file__).resolve().parents[1]
CLOB_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137

log = logging.getLogger("main")


@dataclass(frozen=True)
class Params:
    asset_ids: list[str] = field(default_factory=list)

    # data
    bar_seconds: int = 60      # bar interval
    max_bars: int = 500        # rolling window kept in memory per asset

    # sizing / safety
    order_size_usd: float = 10.0
    cooldown_s: float = 120.0  # min seconds between orders per asset

    # paper trading
    starting_cash: float = 1_000.0
    slippage_bps: float = 20.0

    # mean reversion strategy
    lookback: int = 30         # bars in the rolling mean/std window
    entry_z: float = 2.0       # enter when z-score < -entry_z
    exit_z: float = 0.5        # exit when z-score >= -exit_z (reverted)
    stop_loss_pct: float = 0.15  # exit if price drops this far below entry


# -- strategies ----------------------------------------------------------------

def make_mean_reversion_entry(p: Params) -> EntryRule:
    """Buy when price dips more than ``entry_z`` stdevs below its rolling mean."""

    def entry(book: PriceBook, asset_id: str) -> bool:
        z = _zscore(book, asset_id, p.lookback)
        return z is not None and z < -p.entry_z

    return entry


def make_mean_reversion_exit(p: Params) -> ExitRule:
    """Sell once price reverts toward the mean, or on a hard stop loss."""

    def exit_(book: PriceBook, asset_id: str, pos: Position) -> bool:
        last = book.last_price(asset_id)
        if last is not None and last <= pos.avg_price * (1 - p.stop_loss_pct):
            return True  # stop loss
        z = _zscore(book, asset_id, p.lookback)
        return z is not None and z >= -p.exit_z

    return exit_


def _zscore(book: PriceBook, asset_id: str, lookback: int) -> float | None:
    closes = book.closes(asset_id)
    if len(closes) < lookback:
        return None
    window = closes[-lookback:]
    mean = statistics.fmean(window)
    std = statistics.pstdev(window)
    if std == 0:
        return None
    return (window[-1] - mean) / std


# -- wiring ----------------------------------------------------------------

def build_paper(params: Params) -> Bot:
    from paper_execution import PaperExecution

    book = PriceBook(max_bars=params.max_bars, bar_seconds=params.bar_seconds)
    paper = PaperExecution(
        book,
        starting_cash=params.starting_cash,
        slippage_bps=params.slippage_bps,
        cooldown_s=params.cooldown_s,
    )
    return Bot(
        asset_ids=params.asset_ids,
        price_book=book,
        account=paper,       # PaperExecution doubles as the read-only account
        execution=paper,
        entry_rule=make_mean_reversion_entry(params),
        exit_rule=make_mean_reversion_exit(params),
        order_size_usd=params.order_size_usd,
    )


def build_live(params: Params) -> Bot:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

    from order_execution import OrderExecution
    from polymarket_account import PolymarketAccount

    creds = ApiCreds(
        api_key=os.environ["POLYMARKET_API_KEY"],
        api_secret=os.environ["POLYMARKET_API_SECRET"],
        api_passphrase=os.environ["POLYMARKET_API_PASSPHRASE"],
    )
    # NOTE: if you trade through the Polymarket UI (proxy wallet), pass
    # signature_type=2 and funder=<your proxy wallet address> here.
    client = ClobClient(
        CLOB_HOST,
        key=os.environ["POLYMARKET_PRIVATE_KEY"],
        chain_id=POLYGON_CHAIN_ID,
        creds=creds,
    )
    account = PolymarketAccount(client, address=os.environ["POLYMARKET_ADDRESS"])

    book = PriceBook(max_bars=params.max_bars, bar_seconds=params.bar_seconds)
    return Bot(
        asset_ids=params.asset_ids,
        price_book=book,
        account=account,
        execution=OrderExecution(client, cooldown_s=params.cooldown_s),
        entry_rule=make_mean_reversion_entry(params),
        exit_rule=make_mean_reversion_exit(params),
        order_size_usd=params.order_size_usd,
    )


# -- entry point -------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Polymarket trading bot")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument(
        "--assets",
        required=True,
        help="comma-separated CLOB token ids to trade",
    )
    parser.add_argument("--bar-seconds", type=int, default=Params.bar_seconds)
    parser.add_argument("--order-size", type=float, default=Params.order_size_usd)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    load_dotenv(ROOT / "polymarket.env")

    params = Params(
        asset_ids=[a.strip() for a in args.assets.split(",") if a.strip()],
        bar_seconds=args.bar_seconds,
        order_size_usd=args.order_size,
    )
    if not params.asset_ids:
        raise SystemExit("no asset ids given")

    log.info("mode=%s assets=%s", args.mode, [a[:16] for a in params.asset_ids])
    bot = build_live(params) if args.mode == "live" else build_paper(params)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
