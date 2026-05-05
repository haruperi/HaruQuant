from __future__ import annotations

from backend.agents.chat.ai_chat import AgentConsultationService, ConversationPlan
from backend.agents.chat.ai_chat.models import ConversationState
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class _Payload:
    def __init__(self) -> None:
        self.payload = type(
            "Payload",
            (),
            {
                "summary": type("Summary", (), {"headline": "Dashboard monitoring active strategies"})(),
            },
        )()


def test_agent_consultation_service_selects_risk_specialist_for_risk_task() -> None:
    service = AgentConsultationService()
    plan = ConversationPlan(
        conversation_plan_id="convplan_1",
        user_goal="Explain current risk",
        response_mode="answer",
        task_class="risk_explanation",
        model_tier="premium",
        response_style="warning",
        domain_focus="risk_explanation",
        rationale="risk task",
    )
    artifacts = service.consult(
        plan=plan,
        page_context=_Payload(),
        conversation_state=ConversationState(active_topic="risk"),
        tool_context={},
        tool_results=[
            ToolExecutionResult(
                tool_name="risk_snapshot",
                payload={"headline_metrics": {"var": 0.03, "drawdown": 0.08}},
                latency_ms=5,
                success=True,
            )
        ],
    )

    assert [artifact.agent_name for artifact in artifacts] == ["portfolio_risk_agent"]
    assert "risk specialist evidence" in artifacts[0].summary.lower()


def test_agent_consultation_service_selects_comparison_specialists() -> None:
    service = AgentConsultationService()
    plan = ConversationPlan(
        conversation_plan_id="convplan_2",
        user_goal="Compare optimization runs",
        response_mode="answer",
        task_class="comparison",
        model_tier="premium",
        response_style="compare",
        domain_focus="optimization_comparison",
        rationale="comparison task",
    )
    artifacts = service.consult(
        plan=plan,
        page_context=_Payload(),
        conversation_state=ConversationState(active_topic="comparison"),
        tool_context={},
        tool_results=[
            ToolExecutionResult(
                tool_name="optimization_results",
                payload={
                    "optimization_found": True,
                    "best_score": 1.24,
                    "headline_metrics": {"best_score": 1.24, "best_max_drawdown": 0.12},
                    "top_results": [
                        {"score": 1.24, "max_drawdown": 0.12},
                        {"score": 1.11, "max_drawdown": 0.08},
                    ],
                },
                latency_ms=5,
                success=True,
            ),
            ToolExecutionResult(
                tool_name="backtest_summary",
                payload={
                    "backtest_found": True,
                    "backtest_id": 42,
                    "headline_metrics": {"sharpe_ratio": 1.6, "max_drawdown": 0.1},
                },
                latency_ms=5,
                success=True,
            ),
        ],
    )

    assert [artifact.agent_name for artifact in artifacts] == [
        "optimization_comparison_agent",
        "backtest_explainer_agent",
    ]
