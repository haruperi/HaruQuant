"""Market data MCP tool adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from backend_retiring.mcp.mt5_mcp.models import MCPToolSpec
from haruquant import data as dukascopy
from haruquant.data import normalize_dukascopy_bars


class HistoricalMarketDataGateway(Protocol):
    """Historical market data gateway exposed through the MCP boundary."""

    def fetch(
        self,
        instrument: str,
        interval: str,
        offer_side: str,
        start: datetime,
        end: datetime,
        max_retries: int = 7,
        limit: int = 30_000,
    ): ...


@dataclass(frozen=True)
class DukascopyGateway:
    """Default gateway backed by the Dukascopy HTTP adapter."""

    def fetch(
        self,
        instrument: str,
        interval: str,
        offer_side: str,
        start: datetime,
        end: datetime,
        max_retries: int = 7,
        limit: int = 30_000,
    ):
        return dukascopy.fetch(
            instrument=instrument,
            interval=interval,
            offer_side=offer_side,
            start=start,
            end=end,
            max_retries=max_retries,
            limit=limit,
        )


@dataclass(frozen=True)
class DukascopyMarketDataTools:
    """MCP-facing Dukascopy market data tools."""

    gateway: HistoricalMarketDataGateway

    def fetch_bars(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        interval: str = dukascopy.INTERVAL_MIN_1,
        offer_side: str = dukascopy.OFFER_SIDE_BID,
        max_retries: int = 7,
        limit: int = 30_000,
        max_age_seconds: int = 86_400,
        include_bars: bool = False,
    ) -> dict[str, object]:
        """Fetch and normalize historical bars through the market-data boundary."""

        try:
            bars = self.gateway.fetch(
                instrument=symbol,
                interval=interval,
                offer_side=offer_side,
                start=start,
                end=end,
                max_retries=max_retries,
                limit=limit,
            )
            snapshot = normalize_dukascopy_bars(
                bars,
                symbol=symbol,
                timeframe=timeframe,
                max_age_seconds=max_age_seconds,
            )
            return snapshot.to_payload(include_bars=include_bars)
        except Exception as exc:
            raise RuntimeError(f"Dukascopy fetch failed closed: {exc}") from exc


MARKET_DATA_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec(
        "fetch_dukascopy_bars",
        "read",
        "Fetch and normalize historical OHLCV bars from Dukascopy.",
    ),
)


__all__ = [
    "DukascopyGateway",
    "DukascopyMarketDataTools",
    "HistoricalMarketDataGateway",
    "MARKET_DATA_TOOL_SPECS",
]
