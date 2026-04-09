"""Role-based authorization for MT5 MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .tools import MUTATING_TOOL_SPECS, READ_ONLY_TOOL_SPECS


McpRole = Literal["viewer", "operator", "trader", "risk_manager", "admin"]


class MT5ToolAuthorizationError(PermissionError):
    """Raised when a caller is not allowed to use an MT5 MCP tool."""


@dataclass(frozen=True)
class MT5ToolAuthorizer:
    """Enforce read-only vs mutating tool separation."""

    read_roles: tuple[McpRole, ...] = ("viewer", "operator", "trader", "risk_manager", "admin")
    write_roles: tuple[McpRole, ...] = ("trader", "risk_manager", "admin")

    def authorize(self, *, tool_name: str, role: McpRole) -> None:
        read_tool_names = {tool.name for tool in READ_ONLY_TOOL_SPECS}
        write_tool_names = {tool.name for tool in MUTATING_TOOL_SPECS}

        if tool_name in read_tool_names and role in self.read_roles:
            return
        if tool_name in write_tool_names and role in self.write_roles:
            return
        raise MT5ToolAuthorizationError(f"role '{role}' is not authorized for tool '{tool_name}'")


__all__ = [
    "MT5ToolAuthorizer",
    "MT5ToolAuthorizationError",
]
