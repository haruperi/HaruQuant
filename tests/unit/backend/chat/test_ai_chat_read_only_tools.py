from __future__ import annotations

import os
import sqlite3

from agents.runtime.tool_executor import AIChatReadOnlyToolExecutor, ChatToolCall
from policies.tool_policy import ReadOnlyToolPolicy, ToolPolicyViolation
from tools.read_only.contracts import ReadOnlyToolRequest
from tools.read_only.state import portfolio_summary, strategy_parameters


def test_read_only_policy_blocks_write_tool() -> None:
    policy = ReadOnlyToolPolicy()

    try:
        policy.enforce("place_live_order")
    except ToolPolicyViolation:
        return

    raise AssertionError("write tool should be blocked")


def test_portfolio_summary_uses_page_context_metrics() -> None:
    result = portfolio_summary(
        ReadOnlyToolRequest(
            user_id="u1",
            page_context={
                "payload": {
                    "page_intelligence": {
                        "visibleMetrics": [
                            {"label": "Account Login", "value": 123456},
                            {"label": "Current Equity", "value": 10000.0},
                        ]
                    }
                }
            },
        )
    )

    assert result.status == "success"
    assert result.data["account_login"] == 123456
    assert "page_context:visibleMetrics" in result.sources


def test_executor_degrades_blocked_tool() -> None:
    executor = AIChatReadOnlyToolExecutor(timeout_seconds=1, max_retries=0)
    results = executor.execute(
        [
            ChatToolCall(
                tool_call_id="call-1",
                tool_name="place_live_order",
                parameters={"user_id": "u1"},
            )
        ]
    )

    assert results[0].status == "blocked"
    assert "allowlist" in (results[0].error or "")


def test_strategy_parameters_reads_sqlite_table(tmp_path) -> None:
    db_path = tmp_path / "haruquant.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "create table strategy_versions (strategy_version_id text, strategy_id text, version text, metadata_json text)"
    )
    conn.execute(
        "insert into strategy_versions values ('sv1', 's1', 'v1', '{\"risk\":1}')"
    )
    conn.commit()
    conn.close()

    previous = os.environ.get("HARUQUANT_DB_PATH")
    os.environ["HARUQUANT_DB_PATH"] = str(db_path)
    try:
        result = strategy_parameters(ReadOnlyToolRequest(user_id="u1", strategy_id="s1"))
    finally:
        if previous is None:
            os.environ.pop("HARUQUANT_DB_PATH", None)
        else:
            os.environ["HARUQUANT_DB_PATH"] = previous

    assert result.status == "success"
    assert result.data["strategies"][0]["strategy_id"] == "s1"
    assert result.data["strategies"][0]["metadata_json"] == {"risk": 1}
