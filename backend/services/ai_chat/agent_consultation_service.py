"""Selective specialist-agent consultation for AI chat."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agents.chat import (
        BacktestExplainerAgent,
        FinalResponderAgent,
        KnowledgeRetrievalAgent,
        OptimizationComparisonAgent,
        PortfolioRiskAgent,
    )

from backend.services.ai_chat.models import ConversationPlan, ConversationState, SpecialistAgentArtifact
from backend.services.tool_executor import ToolExecutionResult


class AgentConsultationService:
    """Run bounded specialist agents for chat tasks that benefit from them."""

    def __init__(
        self,
        *,
        backtest_explainer_agent: 'BacktestExplainerAgent | None' = None,
        portfolio_risk_agent: 'PortfolioRiskAgent | None' = None,
        optimization_comparison_agent: 'OptimizationComparisonAgent | None' = None,
        knowledge_retrieval_agent: 'KnowledgeRetrievalAgent | None' = None,
        final_responder_agent: 'FinalResponderAgent | None' = None,
    ) -> None:
        if backtest_explainer_agent is None:
            from backend.agents.chat.backtest_explainer_agent import BacktestExplainerAgent
            self.backtest_explainer_agent = BacktestExplainerAgent()
        else:
            self.backtest_explainer_agent = backtest_explainer_agent
            
        if portfolio_risk_agent is None:
            from backend.agents.chat.portfolio_risk_agent import PortfolioRiskAgent
            self.portfolio_risk_agent = PortfolioRiskAgent()
        else:
            self.portfolio_risk_agent = portfolio_risk_agent
            
        if optimization_comparison_agent is None:
            from backend.agents.chat.optimization_comparison_agent import OptimizationComparisonAgent
            self.optimization_comparison_agent = OptimizationComparisonAgent()
        else:
            self.optimization_comparison_agent = optimization_comparison_agent
            
        if knowledge_retrieval_agent is None:
            from backend.agents.chat.knowledge_retrieval_agent import KnowledgeRetrievalAgent
            self.knowledge_retrieval_agent = KnowledgeRetrievalAgent()
        else:
            self.knowledge_retrieval_agent = knowledge_retrieval_agent
            
        if final_responder_agent is None:
            from backend.agents.chat.final_responder_agent import FinalResponderAgent
            self.final_responder_agent = FinalResponderAgent()
        else:
            self.final_responder_agent = final_responder_agent

    def consult(
        self,
        *,
        plan: ConversationPlan,
        page_context,
        conversation_state: ConversationState,
        tool_context: dict[str, object],
        tool_results: list[ToolExecutionResult],
    ) -> list[SpecialistAgentArtifact]:
        if plan.response_mode not in {"answer", "tool_assisted"}:
            return []

        artifacts: list[SpecialistAgentArtifact] = []
        if plan.task_class == "diagnostic":
            artifact = self.backtest_explainer_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if artifact is not None:
                artifacts.append(artifact)
            fallback_artifact = self.portfolio_risk_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if fallback_artifact is not None and artifact is None:
                artifacts.append(fallback_artifact)
        elif plan.task_class == "risk_explanation":
            artifact = self.portfolio_risk_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if artifact is not None:
                artifacts.append(artifact)
        elif plan.task_class == "comparison":
            artifact = self.optimization_comparison_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if artifact is not None:
                artifacts.append(artifact)
            supplemental = self.backtest_explainer_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if supplemental is not None:
                artifacts.append(supplemental)
        elif plan.task_class == "knowledge_dialogue" or any(
            result.tool_name == "internal_knowledge" and result.success
            for result in tool_results
        ):
            artifact = self.knowledge_retrieval_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts

    def compose_final_response(
        self,
        *,
        user_prompt: str,
        task_class: str,
        page_context,
        tool_results: list[ToolExecutionResult],
        specialist_artifacts: list[SpecialistAgentArtifact],
        default_text: str,
    ) -> str:
        return self.final_responder_agent.compose(
            user_prompt=user_prompt,
            task_class=task_class,
            page_context=page_context,
            tool_results=tool_results,
            specialist_artifacts=specialist_artifacts,
            default_text=default_text,
        )
