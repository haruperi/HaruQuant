"""Unit tests for the upgraded bounded LLM specialist agents."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.chat.backtest_explainer_agent import BacktestExplainerAgent
from backend.agents.chat.final_responder_agent import FinalResponderAgent
from backend.agents.chat.knowledge_retrieval_agent import KnowledgeRetrievalAgent
from backend.agents.chat.optimization_comparison_agent import OptimizationComparisonAgent
from backend.agents.chat.portfolio_risk_agent import PortfolioRiskAgent
from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult


@pytest.fixture
def mock_page_context():
    context = MagicMock()
    context.payload.summary.headline = "Mock Dashboard Headline."
    context.payload.page_type = "generic"
    return context


@pytest.fixture
def mock_tool_context():
    return {}


class TestBacktestExplainerAgent:
    def test_analyze_with_llm_success(self, mock_page_context, mock_tool_context):
        agent = BacktestExplainerAgent()
        tool_results = [
            ToolExecutionResult(
                tool_name="backtest_summary",
                success=True,
                payload={
                    "backtest_found": True,
                    "backtest_id": "bt_123",
                    "headline_metrics": {"sharpe": 1.2, "max_drawdown": "15%"},
                },
                latency_ms=0,
            )
        ]

        expected_llm_output = {
            "summary": "Backtest shows strong Sharpe but moderate drawdown.",
            "findings": ["Sharpe is 1.2", "Drawdown is 15%"],
            "evidence": ["sharpe=1.2", "max_drawdown=15%"],
            "recommendation": "Review trade distribution.",
            "confidence": 85,
            "missing_data": ["profit_factor"],
        }

        with patch("backend.agents.chat.agent_base.create_llm_runtime") as mock_create:
            mock_runtime = MagicMock()
            mock_runtime._call_llm.return_value = {"content": json.dumps(expected_llm_output)}
            mock_create.return_value = mock_runtime

            artifact = agent.analyze(
                task_class="diagnostic",
                tool_results=tool_results,
                page_context=mock_page_context,
                tool_context=mock_tool_context,
            )

            assert artifact is not None
            assert artifact.agent_name == "backtest_explainer_agent"
            assert artifact.summary == "Backtest shows strong Sharpe but moderate drawdown."
            assert len(artifact.findings) == 2
            assert artifact.confidence == 85
            assert any("missing:profit_factor" in src for src in artifact.sources)

    def test_analyze_fallback_on_llm_failure(self, mock_page_context, mock_tool_context):
        agent = BacktestExplainerAgent()
        tool_results = [
            ToolExecutionResult(
                tool_name="backtest_summary",
                success=True,
                payload={"backtest_found": True, "total_trades": 50},
                latency_ms=0,
            )
        ]

        with patch("backend.agents.chat.agent_base.create_llm_runtime") as mock_create:
            mock_runtime = MagicMock()
            # Simulate invalid JSON output to trigger fallback
            mock_runtime._call_llm.return_value = {"content": "not valid json"}
            mock_create.return_value = mock_runtime

            artifact = agent.analyze(
                task_class="diagnostic",
                tool_results=tool_results,
                page_context=mock_page_context,
                tool_context=mock_tool_context,
            )

            assert artifact is not None
            # Fallback summary
            assert "Backtest and strategy evidence suggest" in artifact.summary
            assert artifact.confidence == 76


class TestPortfolioRiskAgent:
    def test_analyze_with_llm_success(self, mock_page_context, mock_tool_context):
        agent = PortfolioRiskAgent()
        tool_results = [
            ToolExecutionResult(
                tool_name="open_positions",
                success=True,
                payload={
                    "open_position_count": 1,
                    "positions": [{"symbol": "EURUSD", "exposure_pct": 55.0}],
                },
                latency_ms=0,
            )
        ]

        expected_llm_output = {
            "summary": "High concentration risk detected.",
            "findings": ["EURUSD exposure is 55.0%"],
            "evidence": ["EURUSD=55.0%"],
            "recommendation": "Reduce EURUSD position size.",
            "confidence": 90,
        }

        with patch("backend.agents.chat.agent_base.create_llm_runtime") as mock_create:
            mock_runtime = MagicMock()
            mock_runtime._call_llm.return_value = {"content": json.dumps(expected_llm_output)}
            mock_create.return_value = mock_runtime

            artifact = agent.analyze(
                task_class="risk_explanation",
                tool_results=tool_results,
                page_context=mock_page_context,
                tool_context=mock_tool_context,
            )

            assert artifact is not None
            assert artifact.summary == "High concentration risk detected."
            assert "EURUSD exposure is 55.0%" in artifact.findings
            assert artifact.confidence == 90


class TestOptimizationComparisonAgent:
    def test_validation_rejects_bad_winner_index(self, mock_page_context, mock_tool_context):
        agent = OptimizationComparisonAgent()
        tool_results = [
            ToolExecutionResult(
                tool_name="optimization_results",
                success=True,
                payload={"optimization_found": True},
                latency_ms=0,
            )
        ]

        expected_llm_output = {
            "summary": "Comparison complete.",
            "findings": ["Candidate A is better"],
            "evidence": ["score=150"],
            "recommendation": "Use A",
            "confidence": 85,
            "winner_index": 5,  # Invalid: must be 0 or 1
        }

        with patch("backend.agents.chat.agent_base.create_llm_runtime") as mock_create:
            mock_runtime = MagicMock()
            mock_runtime._call_llm.return_value = {"content": json.dumps(expected_llm_output)}
            mock_create.return_value = mock_runtime

            artifact = agent.analyze(
                task_class="comparison",
                tool_results=tool_results,
                page_context=mock_page_context,
                tool_context=mock_tool_context,
            )

            assert artifact is not None
            # Because winner_index was invalid, it should hit fallback
            assert "Comparison specialist evidence is available" in artifact.summary


class TestKnowledgeRetrievalAgent:
    def test_analyze_no_matches_returns_none(self, mock_page_context, mock_tool_context):
        agent = KnowledgeRetrievalAgent()
        tool_results = [
            ToolExecutionResult(
                tool_name="internal_knowledge",
                success=True,
                payload={"matches": []},
                latency_ms=0,
            )
        ]

        artifact = agent.analyze(
            task_class="knowledge_dialogue",
            tool_results=tool_results,
            page_context=mock_page_context,
            tool_context=mock_tool_context,
        )

        assert artifact is None


class TestFinalResponderAgent:
    def test_compose_uses_llm_on_high_confidence(self, mock_page_context):
        agent = FinalResponderAgent()
        artifacts = [
            SpecialistAgentArtifact(
                agent_name="test_agent",
                task_class="diagnostic",
                summary="Test summary",
                findings=["Test finding"],
                evidence=["Test evidence"],
                sources=[],
                recommendation="Test recommendation",
                confidence=85,  # High confidence triggers LLM
            )
        ]

        with patch("backend.agents.chat.final_responder_agent.create_llm_runtime") as mock_create:
            mock_runtime = MagicMock()
            mock_runtime._call_llm.return_value = {"content": "This is the LLM composed response."}
            mock_create.return_value = mock_runtime

            response = agent.compose(
                user_prompt="Explain this.",
                task_class="diagnostic",
                page_context=mock_page_context,
                tool_results=[],
                specialist_artifacts=artifacts,
                default_text="Default response.",
            )

            assert response == "This is the LLM composed response."

    def test_compose_uses_fallback_on_low_confidence(self, mock_page_context):
        agent = FinalResponderAgent()
        artifacts = [
            SpecialistAgentArtifact(
                agent_name="test_agent",
                task_class="diagnostic",
                summary="Test summary",
                findings=["Test finding"],
                evidence=["Test evidence"],
                sources=[],
                recommendation="Test recommendation",
                confidence=50,  # Low confidence
            )
        ]

        # No mock needed; it should not call LLM
        response = agent.compose(
            user_prompt="Explain this.",
            task_class="diagnostic",
            page_context=mock_page_context,
            tool_results=[],
            specialist_artifacts=artifacts,
            default_text="Default response.",
        )

        assert "Test summary" in response
        assert "Test finding" in response
        assert "Default response." in response
