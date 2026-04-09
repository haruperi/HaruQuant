from __future__ import annotations

import asyncio
import time

import pytest

from backend.mcp import AsyncMCPCallAdapter


async def _run_call() -> int:
    adapter = AsyncMCPCallAdapter()
    return await adapter.call(lambda: 42)


def test_async_mcp_call_adapter_runs_sync_function_async() -> None:
    result = asyncio.run(_run_call())

    assert result == 42


async def _run_timeout() -> None:
    adapter = AsyncMCPCallAdapter()
    await adapter.call(lambda: time.sleep(0.05), timeout_seconds=0.01)


def test_async_mcp_call_adapter_honors_timeout() -> None:
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(_run_timeout())
