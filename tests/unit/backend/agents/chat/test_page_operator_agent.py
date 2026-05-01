"""Unit tests for the PageOperatorAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.chat.page_operator_agent import PageOperatorAgent


@pytest.fixture
def mock_page_context():
    context = MagicMock()
    context.payload.page_type = "live_trading"
    context.payload.payload = {
        "page_actions": [
            {
                "id": "live_trading.change_symbol",
                "description": "Change the active chart symbol",
                "schema": {"symbol": "string"},
                "riskLevel": "local_ui",
            }
        ]
    }
    context.payload.entity_refs = []
    return context


class TestPageOperatorAgent:
    def test_analyze_with_llm_success(self, mock_page_context):
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan") as mock_call_llm:
            mock_call_llm.return_value = {
                "summary": "I will change the symbol to EURUSD.",
                "findings": ["User requested EURUSD"],
                "evidence": ["live_trading context supports change_symbol"],
                "recommendation": "Review the new chart.",
                "confidence": 90,
                "action_plan": {
                    "action_id": "live_trading.change_symbol",
                    "parameters": {"symbol": "EURUSD"},
                    "risk_level": "local_ui",
                    "reasoning": "User explicitly asked for EURUSD.",
                },
            }

            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="change the symbol to EURUSD",
                page_context=mock_page_context,
            )

            assert artifact is not None
            assert artifact.confidence == 90
            assert artifact.action_plan is not None
            assert artifact.action_plan["action_id"] == "live_trading.change_symbol"
            assert artifact.action_plan["parameters"] == {"symbol": "EURUSD"}

    def test_analyze_missing_actions_graceful_fallback(self, mock_page_context):
        mock_page_context.payload.payload["page_actions"] = []
        agent = PageOperatorAgent()

        artifact = agent.analyze(
            task_class="page_operation",
            user_prompt="change the symbol to EURUSD",
            page_context=mock_page_context,
        )

        assert artifact is not None
        assert artifact.confidence == 100
        assert artifact.action_plan is None
        assert "This page does not currently support automated actions" in artifact.summary

    def test_analyze_llm_unsupported_action(self, mock_page_context):
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan") as mock_call_llm:
            mock_call_llm.return_value = {
                "summary": "I cannot place trades.",
                "findings": ["User requested to buy 100 shares"],
                "evidence": ["live_trading context does not support order execution"],
                "recommendation": "Please do it manually.",
                "confidence": 100,
                "action_plan": None,
            }

            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="buy 100 shares of AAPL",
                page_context=mock_page_context,
            )

            assert artifact is not None
            assert artifact.confidence == 100
            assert artifact.action_plan is None
            assert "I cannot place trades" in artifact.summary

    def test_extra_validate_fails_on_invalid_action_plan(self, mock_page_context):
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan") as mock_call_llm:
            mock_call_llm.return_value = {
                "summary": "I will do something invalid.",
                "findings": ["User requested invalid stuff"],
                "evidence": ["none"],
                "recommendation": "Review.",
                "confidence": 90,
                "action_plan": {
                    "action_id": "live_trading.change_symbol",
                    "parameters": {"symbol": "EURUSD"},
                    "risk_level": "made_up_risk_level",  # INVALID
                    "reasoning": "Because.",
                },
            }

            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="do invalid stuff",
                page_context=mock_page_context,
            )

            # The validation fails, so it triggers fallback.
            assert artifact is not None
            assert artifact.confidence == 0
            assert artifact.action_plan is None
            assert "I cannot perform UI actions at this moment" in artifact.summary
