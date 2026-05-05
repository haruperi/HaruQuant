"""Async wrappers for MCP integration calls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AsyncMCPCallAdapter:
    """Run blocking MCP integration calls in the default thread pool."""

    async def call(
        self,
        fn: Callable[..., Any],
        /,
        *args: Any,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> Any:
        coroutine = asyncio.to_thread(fn, *args, **kwargs)
        if timeout_seconds is None:
            return await coroutine
        return await asyncio.wait_for(coroutine, timeout=timeout_seconds)
