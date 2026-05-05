"""Unit tests for the PageOperatorAgent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend_retiring.agents.chat.page_operator_agent import PageOperatorAgent


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

    def test_analyze_uses_registered_trades_calendar_action_when_llm_refuses(self):
        context = MagicMock()
        context.payload.page_type = "backtest_detail"
        context.payload.payload = {
            "page_intelligence": {
                "actionAffordances": [
                    {
                        "id": "navigate_performance_page",
                        "label": "Navigate Performance Page",
                        "description": "Switch between performance views including Trades Calendar.",
                        "riskLevel": "view_only",
                        "parameters": [
                            {
                                "name": "path",
                                "type": "string",
                                "required": True,
                            }
                        ],
                    }
                ]
            }
        }
        context.payload.entity_refs = []
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan") as mock_call_llm:
            mock_call_llm.return_value = {
                "summary": "This page does not currently support automated actions.",
                "findings": ["No page actions are registered."],
                "evidence": ["page_type=backtest_detail"],
                "recommendation": "Perform the action manually.",
                "confidence": 100,
                "action_plan": None,
            }

            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="Show me the trades calendar for this backtest.",
                page_context=context,
            )

            assert artifact is not None
            assert artifact.action_plan is not None
            assert artifact.action_plan["action_id"] == "navigate_performance_page"
            assert artifact.action_plan["parameters"] == {"path": "trades-calender"}
            assert artifact.action_plan["risk_level"] == "view_only"

    def test_analyze_asks_confirmation_for_llm_inferred_missing_parameter(self):
        context = MagicMock()
        context.payload.page_type = "generic"
        context.payload.payload = {
            "page_intelligence": {
                "actionAffordances": [
                    {
                        "id": "navigate_app_page",
                        "label": "Navigate App Page",
                        "description": "Navigate to a top-level app page.",
                        "riskLevel": "view_only",
                        "parameters": [
                            {
                                "name": "path",
                                "type": "string",
                                "required": True,
                            }
                        ],
                    }
                ]
            }
        }
        context.payload.entity_refs = []
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan") as mock_call_llm:
            mock_call_llm.return_value = {
                "summary": "Likely target is the performance page.",
                "findings": ["User wrote a fuzzy performance navigation request."],
                "evidence": ["allowed action navigate_app_page"],
                "recommendation": "Confirm before navigation.",
                "confidence": 90,
                "action_plan": {
                    "action_id": "navigate_app_page",
                    "parameters": {"path": "/performance"},
                    "risk_level": "view_only",
                    "reasoning": "Fuzzy spelling maps to performance.",
                },
            }

            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="go to prfrmance",
                page_context=context,
            )

            assert artifact is not None
            assert artifact.action_plan is None
            assert "Do you want me to navigate to `/performance`" in artifact.summary
            assert "page_action_confirmation: navigate_app_page" in artifact.summary
            sent_payload = mock_call_llm.call_args.kwargs["user_payload"]
            assert sent_payload["deterministic_result"]["status"] == "needs_input"
            assert any(route["path"] == "/performance" for route in sent_payload["app_route_catalog"])

    def test_analyze_asks_confirmation_from_route_catalog_when_llm_unavailable(self):
        context = MagicMock()
        context.payload.page_type = "generic"
        context.payload.payload = {
            "page_intelligence": {
                "actionAffordances": [
                    {
                        "id": "navigate_app_page",
                        "label": "Navigate App Page",
                        "description": "Navigate to a top-level app page.",
                        "riskLevel": "view_only",
                        "parameters": [
                            {
                                "name": "path",
                                "type": "string",
                                "required": True,
                            }
                        ],
                    }
                ]
            }
        }
        context.payload.entity_refs = []
        agent = PageOperatorAgent()

        with patch.object(agent, "_call_llm_plan", return_value=None):
            artifact = agent.analyze(
                task_class="page_operation",
                user_prompt="go to prfrmance page",
                page_context=context,
            )

            assert artifact is not None
            assert artifact.action_plan is None
            assert "Do you want me to navigate to `/performance`" in artifact.summary
            assert "route_catalog_score=" in artifact.evidence[1]

    def test_analyze_executes_confirmed_inferred_page_action(self):
        context = MagicMock()
        context.payload.page_type = "generic"
        context.payload.payload = {
            "page_intelligence": {
                "actionAffordances": [
                    {
                        "id": "navigate_app_page",
                        "label": "Navigate App Page",
                        "description": "Navigate to a top-level app page.",
                        "riskLevel": "view_only",
                        "parameters": [
                            {
                                "name": "path",
                                "type": "string",
                                "required": True,
                            }
                        ],
                    }
                ]
            }
        }
        context.payload.entity_refs = []
        agent = PageOperatorAgent()

        artifact = agent.analyze(
            task_class="page_operation",
            user_prompt="yes",
            page_context=context,
            tool_context={
                "recent_messages": [
                    {
                        "role": "assistant",
                        "content": "Do you want me to navigate to `/performance`? page_action_confirmation: navigate_app_page {'path': '/performance'}",
                    }
                ]
            },
        )

        assert artifact is not None
        assert artifact.action_plan is not None
        assert artifact.action_plan["action_id"] == "navigate_app_page"
        assert artifact.action_plan["parameters"] == {"path": "/performance"}

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
