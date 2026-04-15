"""Symbol metadata cache models for pre-submit execution validation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.common.logger import logger

class SymbolMetadataCacheEntry(BaseModel):
    """Cached symbol metadata required by execution readiness checks."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    observed_at: datetime
    market_open: bool
    tradable: bool
    supported_fill_modes: tuple[str, ...]
    stop_level_points: int = Field(ge=0)
    freeze_level_points: int = Field(ge=0)
    tick_size: float = Field(gt=0.0)
    point_value: float = Field(gt=0.0)
    contract_size: float = Field(gt=0.0)
    max_age_seconds: int = Field(gt=0)


class SymbolMetadataCache:
    """Small in-memory metadata cache keyed by symbol."""

    def __init__(self) -> None:
        self._entries: dict[str, SymbolMetadataCacheEntry] = {}

    def put(self, entry: SymbolMetadataCacheEntry) -> SymbolMetadataCacheEntry:
        self._entries[entry.symbol] = entry
        return entry

    def get(self, symbol: str) -> SymbolMetadataCacheEntry | None:
        return self._entries.get(symbol)

    def get_many(self, symbols: tuple[str, ...]) -> dict[str, SymbolMetadataCacheEntry]:
        return {
            symbol: entry
            for symbol in symbols
            if (entry := self._entries.get(symbol)) is not None
        }
