"""Shared MT5 MCP model types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MCPToolSpec:
    """Static MCP tool metadata exposed by the server."""

    name: str
    mode: str
    description: str


__all__ = ["MCPToolSpec"]
