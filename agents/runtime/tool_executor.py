"""Tool execution logic for HaruQuant agents."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agents.runtime.tool_policy import ReadOnlyToolPolicy, ToolPolicyViolation
from tools.read_only import READ_ONLY_TOOLS
from tools.read_only.contracts import ReadOnlyToolRequest, ReadOnlyToolResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCall:
    tool_call_id: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    tool_name: str
    output: Any
    status: str = "success"
    error: Optional[str] = None


class ToolExecutor:
    """Executes a list of tool calls against a registry of callables."""

    def __init__(self, tools: Dict[str, Any]) -> None:
        self.tools = tools

    def execute(self, calls: List[ToolCall]) -> List[ToolResult]:
        results = []
        for call in calls:
            tool_func = self.tools.get(call.tool_name)
            if not tool_func:
                results.append(ToolResult(
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    output=None,
                    status="failed",
                    error=f"Tool '{call.tool_name}' not found."
                ))
                continue
            
            try:
                # Handle both synchronous and asynchronous (not handled here for simplicity)
                output = tool_func(**call.parameters)
                results.append(ToolResult(
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    output=output
                ))
            except Exception as exc:
                results.append(ToolResult(
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    output=None,
                    status="failed",
                    error=str(exc)
                ))
        return results


@dataclass(frozen=True)
class ChatToolCall:
    tool_call_id: str
    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)


class AIChatReadOnlyToolExecutor:
    """Executes only allowlisted read-only HaruQuant tools for AI Chat."""

    def __init__(
        self,
        *,
        policy: ReadOnlyToolPolicy | None = None,
        timeout_seconds: float = 3.0,
        max_retries: int = 1,
    ) -> None:
        self.policy = policy or ReadOnlyToolPolicy()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def execute(self, calls: list[ChatToolCall]) -> list[ReadOnlyToolResult]:
        results: list[ReadOnlyToolResult] = []
        for call in calls:
            results.append(self._execute_one(call))
        return results

    def _execute_one(self, call: ChatToolCall) -> ReadOnlyToolResult:
        started = time.perf_counter()
        try:
            self.policy.enforce(call.tool_name)
            tool = READ_ONLY_TOOLS.get(call.tool_name)
            if tool is None:
                raise ToolPolicyViolation(f"Tool '{call.tool_name}' is not implemented.")
            request = ReadOnlyToolRequest(**call.parameters)
        except Exception as exc:
            logger.warning(
                "ai_chat_read_only_tool_blocked",
                extra={"tool_name": call.tool_name, "tool_call_id": call.tool_call_id, "error": str(exc)},
            )
            return ReadOnlyToolResult(
                tool_name=call.tool_name,
                status="blocked",
                summary=f"Tool blocked: {exc}",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=str(exc),
            )

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(tool, request)
                    result = future.result(timeout=self.timeout_seconds)
                final = result.model_copy(
                    update={"latency_ms": int((time.perf_counter() - started) * 1000)}
                )
                logger.info(
                    "ai_chat_read_only_tool_completed",
                    extra={
                        "tool_name": call.tool_name,
                        "tool_call_id": call.tool_call_id,
                        "status": final.status,
                        "latency_ms": final.latency_ms,
                    },
                )
                return final
            except FutureTimeout:
                last_error = f"Timed out after {self.timeout_seconds:.1f}s"
            except Exception as exc:  # pragma: no cover - adapter dependent
                last_error = str(exc)
            if attempt < self.max_retries:
                continue
        logger.warning(
            "ai_chat_read_only_tool_failed",
            extra={"tool_name": call.tool_name, "tool_call_id": call.tool_call_id, "error": last_error},
        )
        return ReadOnlyToolResult(
            tool_name=call.tool_name,
            status="failed",
            summary=f"Tool failed gracefully: {last_error or 'unknown error'}",
            latency_ms=int((time.perf_counter() - started) * 1000),
            error=last_error,
        )


def tool_results_as_prompt(results: list[ReadOnlyToolResult]) -> str:
    payload = [
        {
            "tool_name": result.tool_name,
            "status": result.status,
            "summary": result.summary,
            "data": result.data,
            "sources": result.sources,
            "error": result.error,
        }
        for result in results
    ]
    return json.dumps(payload, default=str, ensure_ascii=True, separators=(",", ":"))


def make_tool_call(tool_name: str, **parameters: Any) -> ChatToolCall:
    return ChatToolCall(
        tool_call_id=f"tool-{uuid4()}",
        tool_name=tool_name,
        parameters=parameters,
    )
