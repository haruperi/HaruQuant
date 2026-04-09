from backend.mcp.mt5_mcp import MT5MCPServer, create_mt5_mcp_server


def test_mt5_mcp_server_starts_with_empty_tool_registry() -> None:
    server = create_mt5_mcp_server()

    assert isinstance(server, MT5MCPServer)
    assert server.name == "mt5_mcp"
    assert server.started is False
    assert server.list_tools() == ()


def test_mt5_mcp_server_startup_marks_server_ready() -> None:
    server = create_mt5_mcp_server()

    result = server.startup()

    assert result is server
    assert server.started is True
