from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from backend_retiring.mcp.market_data_mcp import (
    DukascopyMarketDataTools,
    create_market_data_mcp_server,
)


class FakeDukascopyGateway:
    def fetch(self, **kwargs):
        self.kwargs = kwargs
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-04-12T08:00:00Z"]),
                "open": [1.1],
                "high": [1.2],
                "low": [1.0],
                "close": [1.15],
                "volume": [100.0],
            }
        )


class FailingDukascopyGateway:
    def fetch(self, **kwargs):
        raise TimeoutError("provider timeout")


def test_market_data_mcp_server_lists_dukascopy_read_tool() -> None:
    server = create_market_data_mcp_server().startup()

    assert server.name == "market_data_mcp"
    assert server.started is True
    assert [tool.name for tool in server.list_tools()] == ["fetch_dukascopy_bars"]
    assert server.list_tools()[0].mode == "read"


def test_dukascopy_mcp_tool_fetches_normalizes_and_returns_freshness_metadata() -> None:
    gateway = FakeDukascopyGateway()
    tools = DukascopyMarketDataTools(gateway=gateway)

    payload = tools.fetch_bars(
        symbol="EURUSD",
        timeframe="M1",
        start=datetime(2026, 4, 12, 7, 0, tzinfo=UTC),
        end=datetime(2026, 4, 12, 8, 0, tzinfo=UTC),
        max_age_seconds=120,
        include_bars=True,
    )

    assert payload["source"] == "dukascopy"
    assert payload["symbol"] == "EURUSD"
    assert payload["timeframe"] == "M1"
    assert payload["row_count"] == 1
    assert payload["max_age_seconds"] == 120
    assert payload["bars"][0]["close"] == 1.15
    assert gateway.kwargs["instrument"] == "EURUSD"


def test_dukascopy_mcp_tool_fails_closed_on_provider_error() -> None:
    tools = DukascopyMarketDataTools(gateway=FailingDukascopyGateway())

    with pytest.raises(RuntimeError, match="Dukascopy fetch failed closed"):
        tools.fetch_bars(
            symbol="EURUSD",
            timeframe="M1",
            start=datetime(2026, 4, 12, 7, 0, tzinfo=UTC),
            end=datetime(2026, 4, 12, 8, 0, tzinfo=UTC),
        )
