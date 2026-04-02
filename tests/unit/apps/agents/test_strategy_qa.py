from __future__ import annotations

import json

from apps.agents.core.agent_models import AgentTask, ToolSpec
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import PermissionTier, load_agent_settings
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.strategy_qa import StrategyQAAgent
from apps.agents.workflows.strategy_promotion_review import run_strategy_promotion_review


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec("backtest_get_run", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {"backtest_id": kwargs["backtest_id"], "status": "completed"},
    )
    registry.register(
        ToolSpec("backtest_get_finance_metrics", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {
            "summary": {
                "profit_factor": 1.7,
                "sharpe_ratio": 1.2,
                "win_rate": 49.0,
            }
        },
    )
    registry.register(
        ToolSpec("optimization_get_run", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {"optimization_id": kwargs["optimization_id"], "status": "completed"},
    )
    registry.register(
        ToolSpec("optimization_get_top_results", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: [{"backtest_id": 101, "score": 9.2, "rank": 1}],
    )
    registry.register(
        ToolSpec("validation_get_wfo_summary", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {"consistency_score": 66.0},
    )
    registry.register(
        ToolSpec("validation_get_manifest", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {"id": kwargs["strategy_version_id"], "version": "1.0.0"},
    )
    registry.register(
        ToolSpec("validation_get_monte_carlo_summary", "validation", PermissionTier.READ_ONLY),
        lambda **kwargs: {"probability_of_ruin": 0.12},
    )
    return registry


def test_planner_routes_strategy_promotion_review():
    plan = AgentPlanner().plan(
        AgentTask(
            task_id="qa-plan",
            task_type="strategy_promotion_review",
            actor_user_id=1,
            actor_role="owner",
            scope="validation",
            intent="strategy_promotion_review",
            input_payload={"backtest_id": 1, "optimization_id": 2, "strategy_version_id": 3},
        )
    )

    assert plan.workflow_name == "strategy_promotion_review"
    assert "backtest_id" in plan.required_inputs


def test_strategy_qa_uses_registry_and_returns_promote_decision():
    agent = StrategyQAAgent(_build_registry())
    result = agent.run(
        AgentTask(
            task_id="qa-1",
            task_type="strategy_promotion_review",
            actor_user_id=1,
            actor_role="owner",
            scope="validation",
            intent="strategy_promotion_review",
            input_payload={
                "backtest_id": 101,
                "optimization_id": 22,
                "strategy_version_id": 7,
                "monte_carlo_id": 9,
            },
            correlation_id="corr-qa",
        )
    )

    assert result.status == "ok"
    assert result.metadata["decision"] == "promote"
    assert any(item["type"] == "strategy_manifest" for item in result.evidence)


def test_strategy_promotion_review_workflow_writes_audit(tmp_path):
    audit_path = tmp_path / "strategy_qa.jsonl"
    result = run_strategy_promotion_review(
        AgentTask(
            task_id="qa-2",
            task_type="strategy_promotion_review",
            actor_user_id=3,
            actor_role="pm",
            scope="validation",
            intent="strategy_promotion_review",
            input_payload={"backtest_id": 11, "optimization_id": 12, "strategy_version_id": 13},
            correlation_id="corr-qa-2",
            run_id="run-qa-2",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(audit_path),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=StrategyQAAgent(_build_registry()),
    )

    assert result.status == "ok"
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["workflow_name"] == "strategy_promotion_review"
