"""Contracts for AI Chat read-only HaruQuant tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ToolStatus = Literal["success", "unavailable", "failed", "blocked"]


class ReadOnlyToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    thread_id: str | None = None
    symbol: str | None = None
    strategy_id: str | None = None
    backtest_id: str | int | None = None
    optimization_id: str | int | None = None
    session_id: int | None = None
    limit: int = 10
    page_context: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class ReadOnlyToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: ToolStatus
    data: dict[str, Any] = Field(default_factory=dict)
    summary: str
    sources: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None


class ReadOnlyToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str
    display_name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


__all__ = ["ReadOnlyToolDefinition", "ReadOnlyToolRequest", "ReadOnlyToolResult", "ToolStatus"]
