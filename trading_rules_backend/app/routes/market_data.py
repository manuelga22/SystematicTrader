
from fastapi import APIRouter, Depends, HTTPException, status

from util.data_processor import TickDataIntervalEnum
from util.log_service import LogService

from trading_rules_backend.app import cache
from trading_rules_backend.app import schemas

from data_clients import polymarket_client as pc

logsvc = LogService("")
router = APIRouter(prefix="/market-data", tags=["rules"])


@router.post("/", response_model=schemas.MarketDataSummary)
async def fetch_polymarket_market_data(req: schemas.FetchMarketDataRequest):
    """Fetch price data from Polymarket, cache it, return a summary + data_id.
       This endpoint DOES NOT RETURN THE FULL MARKET DATA, it just stores it in the server-side cache.
    """
    
    client = pc.PolymarketAPIClient()
 
    prices = await client.get_price_history_by_outcome(
        market_slug=req.market_slug,
        outcome=req.outcome.value,
        start_ts=req.start_ts,
        end_ts=req.end_ts,
        interval=TickDataIntervalEnum(req.interval),
    )
 
    if not prices:
        raise HTTPException(status_code=404, detail="No price data returned for this slug/timeframe.")
 
    entry = cache.CacheEntry(
        market_slug=req.market_slug,
        outcome=req.outcome.value,
        interval=req.interval,
        start_ts=req.start_ts,
        end_ts=req.end_ts,
        prices=prices,
    )

    # Insert the entry in the cache for future reference
    data_id = cache.put(entry)
 
    return schemas.MarketDataSummary(
        data_id=data_id,
        market_slug=req.market_slug,
        outcome=req.outcome,
        interval=req.interval,
        start_ts=req.start_ts,
        end_ts=req.end_ts,
        row_count=len(prices),
    )


@router.get("/{data_id}", response_model=schemas.MarketDataFull)
async def fetch_polymarket_market_data(data_id: str):
    """Return the full cached price series (for frontend charting)."""
 
    entry = cache.get(data_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="data_id not found or expired.")
 
    return schemas.MarketDataFull(
        data_id=data_id,
        market_slug=entry.market_slug,
        outcome=entry.outcome,
        prices=entry.prices,
    )
