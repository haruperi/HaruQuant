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
        PageOperatorAgent,
        TradingAdvisorAgent,
        MarketRegimeAgent,
        StrategyCodeReviewAgent,
    )

from backend.agents.chat.ai_chat.models import ConversationPlan, ConversationState, SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult


class AgentConsultationService:
    """Run bounded specialist agents for chat tasks that benefit from them."""

    def __init__(
        self,
        *,
        backtest_explainer_agent: 'BacktestExplainerAgent | None' = None,
        portfolio_risk_agent: 'PortfolioRiskAgent | None' = None,
        optimization_comparison_agent: 'OptimizationComparisonAgent | None' = None,
        knowledge_retrieval_agent: 'KnowledgeRetrievalAgent | None' = None,
        page_operator_agent: 'PageOperatorAgent | None' = None,
        trading_advisor_agent: 'TradingAdvisorAgent | None' = None,
        market_regime_agent: 'MarketRegimeAgent | None' = None,
        strategy_code_review_agent: 'StrategyCodeReviewAgent | None' = None,
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

        if page_operator_agent is None:
            from backend.agents.chat.page_operator_agent import PageOperatorAgent
            self.page_operator_agent = PageOperatorAgent()
        else:
            self.page_operator_agent = page_operator_agent

        if trading_advisor_agent is None:
            from backend.agents.chat.trading_advisor_agent import TradingAdvisorAgent
            self.trading_advisor_agent = TradingAdvisorAgent()
        else:
            self.trading_advisor_agent = trading_advisor_agent

        if market_regime_agent is None:
            from backend.agents.chat.market_regime_agent import MarketRegimeAgent
            self.market_regime_agent = MarketRegimeAgent()
        else:
            self.market_regime_agent = market_regime_agent

        if strategy_code_review_agent is None:
            from backend.agents.chat.strategy_code_review_agent import StrategyCodeReviewAgent
            self.strategy_code_review_agent = StrategyCodeReviewAgent()
        else:
            self.strategy_code_review_agent = strategy_code_review_agent

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
        if plan.task_class == "strategy_creation":
            # Strategy creation is owned by backend.agents.strategy_creator_agent.StrategyCreatorAgent.
            # This service only adds supplemental review if a rendered script is present.
            review = self.strategy_code_review_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if review is not None:
                artifacts.append(review)
        elif plan.task_class == "diagnostic":
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
        elif plan.task_class == "page_operation":
            # This task passes user prompt specifically if needed,
            # but AgentConsultationService currently doesn't receive `user_prompt` in `consult`.
            # Wait, `consult` method does not have `user_prompt`. Let's just pass `page_context`.
            # The agent signature requires `user_prompt`. We must modify `consult` signature or
            # `PageOperatorAgent` signature or pass `user_prompt` down.
            # I will pass `user_prompt=plan.user_goal` to the agent.
            artifact = self.page_operator_agent.analyze(
                task_class=plan.task_class,
                user_prompt=plan.user_goal,
                page_context=page_context,
                tool_results=tool_results,
                tool_context=tool_context,
            )
            if artifact is not None:
                artifacts.append(artifact)

        # Market regime analysis for relevant tasks
        if plan.task_class in {"diagnostic", "recommendation", "risk_explanation", "performance_summary"}:
            regime = self.market_regime_agent.analyze(
                task_class=plan.task_class,
                tool_results=tool_results,
                page_context=page_context,
                tool_context=tool_context,
            )
            if regime is not None:
                artifacts.append(regime)

        # General strategic advice fallback for appropriate task classes
        if plan.task_class in {"recommendation", "performance_summary"} and not artifacts:
            artifact = self.trading_advisor_agent.analyze(
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
