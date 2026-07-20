from enum import Enum

from pydantic import BaseModel
from util.data_processor import TickDataIntervalEnum

class Outcome(str, Enum):
    YES = "yes"
    NO = "no"


class FetchMarketDataRequest(BaseModel):
    market_slug: str
    outcome: Outcome
    start_ts: int          # unix epoch seconds
    end_ts: int            # unix epoch seconds
    interval: str = "1h"   # e.g. "1m", "5m", "1h", 

class MarketDataSummary(BaseModel):
    """Returned after caching — lightweight enough to send every time."""
    data_id: str
    market_slug: str
    outcome: Outcome
    interval: str
    start_ts: int
    end_ts: int
    row_count: int


class MarketDataFull(BaseModel):
    """Only returned when the frontend explicitly asks for the series."""
    data_id: str
    market_slug: str
    outcome: Outcome
    prices: dict


class BacktestRequest(BaseModel):
    entry_rules: list
    exit_rules: list
    data_id: str
    initial_capital: float = 10000.0
