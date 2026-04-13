"""Tests for Phase 2: Native Tool Calling (ToolCall, ToolResult, ToolExecutor)."""

from __future__ import annotations

import json
import time

import pytest

from backend.agents.runtime import (
    ToolCall,
    ToolResult,
    ToolExecutor,
    _estimate_tokens,
)


# ──────────────────────────────────────────────────────────────
# ToolCall model tests
# ──────────────────────────────────────────────────────────────

def test_tool_call_creation() -> None:
    """ToolCall should be created with required fields."""
    tc = ToolCall(
        tool_call_id="call_001",
        tool_name="get_weather",
        parameters={"location": "NYC", "units": "metric"},
    )
    assert tc.tool_call_id == "call_001"
    assert tc.tool_name == "get_weather"
    assert tc.parameters["location"] == "NYC"
    assert tc.metadata == {}  # default


def test_tool_call_with_metadata() -> None:
    """ToolCall should support optional metadata."""
    tc = ToolCall(
        tool_call_id="call_002",
        tool_name="search",
        parameters={"query": "test"},
        metadata={"source": "user_input"},
    )
    assert tc.metadata["source"] == "user_input"


# ──────────────────────────────────────────────────────────────
# ToolResult model tests
# ──────────────────────────────────────────────────────────────

def test_tool_result_success() -> None:
    """ToolResult should capture successful output."""
    tr = ToolResult(
        tool_call_id="call_001",
        tool_name="get_weather",
        output='{"temp": 72}',
        token_count=10,
        latency_ms=50,
    )
    assert tr.is_error is False
    assert tr.error is None
    assert "temp" in tr.output


def test_tool_result_error() -> None:
    """ToolResult should capture error state."""
    tr = ToolResult(
        tool_call_id="call_001",
        tool_name="get_weather",
        output="Error: API unavailable",
        error="API unavailable",
        is_error=True,
    )
    assert tr.is_error is True
    assert tr.error == "API unavailable"


# ──────────────────────────────────────────────────────────────
# Token estimation tests
# ──────────────────────────────────────────────────────────────

def test_estimate_tokens_short() -> None:
    """Short strings should estimate to ~1/4 of length."""
    text = "hello world"
    tokens = _estimate_tokens(text)
    assert tokens == max(1, len(text) // 4)


def test_estimate_tokens_long() -> None:
    """Long strings should estimate proportionally."""
    text = "x" * 4000
    tokens = _estimate_tokens(text)
    assert tokens == 1000


def test_estimate_tokens_empty() -> None:
    """Empty strings should return at least 1."""
    assert _estimate_tokens("") >= 1


# ──────────────────────────────────────────────────────────────
# ToolExecutor tests
# ──────────────────────────────────────────────────────────────

def test_tool_executor_executes_known_tool() -> None:
    """Executor should call registered tools and return results."""
    def get_weather(location: str, units: str = "metric") -> dict:
        return {"location": location, "temp": 72, "units": units}

    executor = ToolExecutor(tools={"get_weather": get_weather})
    results = executor.execute([
        ToolCall(
            tool_call_id="call_001",
            tool_name="get_weather",
            parameters={"location": "NYC", "units": "imperial"},
        ),
    ])

    assert len(results) == 1
    assert results[0].tool_call_id == "call_001"
    assert results[0].is_error is False
    output = json.loads(results[0].output)
    assert output["location"] == "NYC"
    assert output["temp"] == 72
    assert results[0].latency_ms >= 0


def test_tool_executor_handles_unknown_tool() -> None:
    """Executor should return error for unknown tools."""
    executor = ToolExecutor(tools={})
    results = executor.execute([
        ToolCall(tool_call_id="call_001", tool_name="nonexistent", parameters={}),
    ])

    assert len(results) == 1
    assert results[0].is_error is True
    assert "nonexistent" in results[0].error


def test_tool_executor_handles_tool_exception() -> None:
    """Executor should catch exceptions and return error result."""
    def failing_tool() -> dict:
        raise RuntimeError("Something went wrong")

    executor = ToolExecutor(tools={"failing": failing_tool})
    results = executor.execute([
        ToolCall(tool_call_id="call_001", tool_name="failing", parameters={}),
    ])

    assert len(results) == 1
    assert results[0].is_error is True
    assert "Something went wrong" in results[0].error


def test_tool_executor_multiple_calls() -> None:
    """Executor should handle multiple tool calls in one batch."""
    executor = ToolExecutor(tools={
        "add": lambda a, b: a + b,
        "multiply": lambda a, b: a * b,
    })
    results = executor.execute([
        ToolCall(tool_call_id="call_1", tool_name="add", parameters={"a": 2, "b": 3}),
        ToolCall(tool_call_id="call_2", tool_name="multiply", parameters={"a": 4, "b": 5}),
        ToolCall(tool_call_id="call_3", tool_name="unknown", parameters={}),
    ])

    assert len(results) == 3
    assert json.loads(results[0].output) == 5
    assert json.loads(results[1].output) == 20
    assert results[2].is_error is True


def test_tool_executor_truncates_large_output() -> None:
    """Executor should truncate oversized tool outputs."""
    def large_output() -> str:
        return "x" * 100000

    executor = ToolExecutor(tools={"large": large_output}, max_output_tokens=1000)
    results = executor.execute([
        ToolCall(tool_call_id="call_001", tool_name="large", parameters={}),
    ])

    assert len(results[0].output) < 100000
    assert "...[truncated]" in results[0].output


def test_tool_executor_execute_one() -> None:
    """execute_one should handle a single call."""
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    executor = ToolExecutor(tools={"greet": greet})
    result = executor.execute_one(
        ToolCall(tool_call_id="call_001", tool_name="greet", parameters={"name": "World"})
    )

    assert result.output == "Hello, World!"
    assert result.is_error is False
