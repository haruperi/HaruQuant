"""Backtest MCP tool adapters over legacy simulation services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from haruquant.utils import logger
from backend_retiring.mcp.mt5_mcp.models import MCPToolSpec


class SimulationCoordinatorGateway(Protocol):
    """Minimal simulation coordinator surface used by the backtest MCP adapter."""

    def get_metadata(self, session_id: int) -> Any: ...

    def get_runtime_owner(self, session_id: int) -> str | None: ...


class SimulationRuntimeGateway(Protocol):
    """Minimal runtime-store surface used by the backtest MCP adapter."""

    def get(self, session_id: int) -> Any: ...


def _normalize_record(record: Any) -> dict[str, Any]:
    if record is None:
        return {}
    if isinstance(record, dict):
        return record
    if hasattr(record, "__dict__"):
        return {
            key: value
            for key, value in vars(record).items()
            if not key.startswith("_")
        }
    return {"value": record}


@dataclass(frozen=True)
class BacktestCoordinatorView:
    """Read-only adapter over simulation coordinator metadata."""

    coordinator: SimulationCoordinatorGateway

    def get_session_metadata(self, session_id: int) -> dict[str, Any]:
        metadata = _normalize_record(self.coordinator.get_metadata(session_id))
        metadata["session_id"] = int(session_id)
        metadata["runtime_owner"] = self.coordinator.get_runtime_owner(session_id)
        return metadata

    def get_runtime_owner(self, session_id: int) -> dict[str, Any]:
        return {
            "session_id": int(session_id),
            "runtime_owner": self.coordinator.get_runtime_owner(session_id),
        }


@dataclass(frozen=True)
class BacktestRuntimeView:
    """Read-only adapter over the in-memory simulation runtime store."""

    runtimes: SimulationRuntimeGateway

    def get_runtime_presence(self, session_id: int) -> dict[str, Any]:
        return {
            "session_id": int(session_id),
            "active": self.runtimes.get(session_id) is not None,
        }


BACKTEST_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("get_session_metadata", "read", "Read legacy simulation session metadata."),
    MCPToolSpec("get_runtime_owner", "read", "Read the current simulation worker lease owner."),
    MCPToolSpec("get_runtime_presence", "read", "Check whether a simulation runtime is attached in-process."),
)


__all__ = [
    "BACKTEST_TOOL_SPECS",
    "BacktestCoordinatorView",
    "BacktestRuntimeView",
]
