"""Tool call execution loop — dispatches tool calls and feeds results back."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from services.utils.logger import logger
from .tool_call import ToolCall, ToolResult


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


class ToolExecutor:
    """Dispatches tool calls and collects results.

    Usage:
        executor = ToolExecutor(tools={
            "get_weather": lambda location: {"temp": 72, "unit": "F"},
            "search": lambda query: [{"title": "Result 1"}],
        })
        results = executor.execute([
            ToolCall(tool_call_id="call_1", tool_name="get_weather", parameters={"location": "NYC"}),
        ])
    """

    def __init__(
        self,
        tools: dict[str, Callable],
        max_output_tokens: int = 4096,
    ) -> None:
        self._tools = tools
        self._max_output_tokens = max_output_tokens

    def execute(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute a list of tool calls and return results."""
        results = []
        for tc in tool_calls:
            results.append(self._execute_one(tc))
        return results

    def execute_one(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        return self._execute_one(tool_call)

    def _execute_one(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call with timing and error handling."""
        started = time.monotonic()
        if tool_call.tool_name not in self._tools:
            return ToolResult(
                tool_call_id=tool_call.tool_call_id,
                tool_name=tool_call.tool_name,
                output=f"Error: unknown tool '{tool_call.tool_name}'",
                error=f"Unknown tool: {tool_call.tool_name}",
                is_error=True,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        try:
            fn = self._tools[tool_call.tool_name]
            output = fn(**tool_call.parameters)
            output_str = json.dumps(output, default=str) if isinstance(output, dict) else str(output)

            # Truncate if too large
            if len(output_str) > self._max_output_tokens * 4:
                output_str = output_str[: self._max_output_tokens * 4] + "\n...[truncated]"

            return ToolResult(
                tool_call_id=tool_call.tool_call_id,
                tool_name=tool_call.tool_name,
                output=output_str,
                token_count=_estimate_tokens(output_str),
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:
            return ToolResult(
                tool_call_id=tool_call.tool_call_id,
                tool_name=tool_call.tool_name,
                output=f"Error: {exc}",
                error=str(exc),
                is_error=True,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
