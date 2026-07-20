from __future__ import annotations
 
import uuid
import time
from dataclasses import dataclass, field
 
# How long a cache entry lives before eviction (seconds).
TTL_SECONDS: int = 60 * 60  # 1 hour
 
 
@dataclass
class CacheEntry:
    slug: str
    outcome: str
    interval: str
    start_ts: int
    end_ts: int
    prices: dict # pd.DataFrame
    created_at: float = field(default_factory=time.time)
 
    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > TTL_SECONDS
 
 
# ── Module-level store ───────────────────────────────────────
 
_store: dict[str, CacheEntry] = {}
 
 
def put(entry: CacheEntry) -> str:
    """Cache a new entry, return its data_id."""
    _evict_expired()
    data_id = uuid.uuid4().hex[:12]
    _store[data_id] = entry
    return data_id
 
 
def get(data_id: str) -> CacheEntry | None:
    """Retrieve a cached entry, or None if missing / expired."""
    entry = _store.get(data_id)
    if entry is None:
        return None
    if entry.is_expired:
        _store.pop(data_id, None)
        return None
    return entry
 
 
def _evict_expired() -> None:
    """Lazy sweep — runs on every put() to keep memory bounded."""
    expired = [k for k, v in _store.items() if v.is_expired]
    for k in expired:
        del _store[k]