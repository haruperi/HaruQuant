from __future__ import annotations

from dataclasses import dataclass

from backend_retiring.mcp.backtest_mcp import (
    BACKTEST_TOOL_SPECS,
    BacktestCoordinatorView,
    BacktestMCPServer,
    BacktestRuntimeView,
    create_backtest_mcp_server,
)


@dataclass(frozen=True)
class FakeMetadata:
    user_id: int
    status: str


class FakeCoordinator:
    def get_metadata(self, session_id: int) -> FakeMetadata | None:
        if session_id == 42:
            return FakeMetadata(user_id=7, status="running")
        return None

    def get_runtime_owner(self, session_id: int) -> str | None:
        return "sim-worker-1" if session_id == 42 else None


class FakeRuntimes:
    def get(self, session_id: int) -> object | None:
        return object() if session_id == 42 else None


def test_backtest_mcp_server_starts_with_expected_tool_specs() -> None:
    server = create_backtest_mcp_server()

    assert isinstance(server, BacktestMCPServer)
    assert server.name == "backtest_mcp"
    assert server.started is False
    assert server.list_tools() == BACKTEST_TOOL_SPECS


def test_backtest_mcp_server_startup_marks_server_ready() -> None:
    server = create_backtest_mcp_server()

    result = server.startup()

    assert result is server
    assert server.started is True


def test_backtest_views_expose_metadata_owner_and_runtime_presence() -> None:
    coordinator = BacktestCoordinatorView(FakeCoordinator())
    runtimes = BacktestRuntimeView(FakeRuntimes())

    metadata = coordinator.get_session_metadata(42)
    owner = coordinator.get_runtime_owner(42)
    presence = runtimes.get_runtime_presence(42)

    assert metadata["user_id"] == 7
    assert metadata["status"] == "running"
    assert metadata["runtime_owner"] == "sim-worker-1"
    assert owner == {"session_id": 42, "runtime_owner": "sim-worker-1"}
    assert presence == {"session_id": 42, "active": True}
