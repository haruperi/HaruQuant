"""Tests for API router and intent router agent."""

from __future__ import annotations

import pytest

from backend_retiring.agents.intent_router import IntentRouterAgent, IntentRouterError
from backend_retiring.agents.route_decision import RouteDecisionService
from backend_retiring.api.router import Intent, IntentClassifier, RoutingMetadata


class TestIntentClassifier:
    def test_classify_market_data(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/dashboard/broker") == Intent.MARKET_DATA

    def test_classify_research(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/strategies/list") == Intent.RESEARCH
        assert c.classify("/api/edge-lab/run") == Intent.RESEARCH

    def test_classify_backtest(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/backtest/run") == Intent.BACKTEST
        assert c.classify("/api/simulator/start") == Intent.BACKTEST

    def test_classify_risk(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/risk/governance") == Intent.RISK

    def test_classify_live_trading(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/live/sessions") == Intent.LIVE_TRADING

    def test_classify_optimization(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/optimization/runs") == Intent.OPTIMIZATION

    def test_classify_settings(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/settings/update") == Intent.SETTINGS

    def test_classify_auth(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/auth/login") == Intent.AUTH

    def test_classify_unknown(self) -> None:
        c = IntentClassifier()
        assert c.classify("/api/nonexistent/path") == Intent.UNKNOWN

    def test_add_route(self) -> None:
        c = IntentClassifier()
        c.add_route("/api/custom", Intent.RESEARCH)
        assert c.classify("/api/custom/test") == Intent.RESEARCH

    def test_classify_and_metadata(self) -> None:
        c = IntentClassifier()
        meta = c.classify_and_metadata(
            "/api/risk/check", priority=5, session_id="s1", user_id=42,
        )
        assert meta.intent == Intent.RISK
        assert meta.priority == 5
        assert meta.session_id == "s1"
        assert meta.user_id == 42

    def test_allowed_intents(self) -> None:
        c = IntentClassifier()
        intents = c.allowed_intents()
        assert Intent.RISK in intents
        assert Intent.BACKTEST in intents

    def test_route_map_is_copy(self) -> None:
        c = IntentClassifier()
        route_map = c.route_map
        route_map["/api/changed"] = Intent.RISK
        assert c.classify("/api/changed") == Intent.UNKNOWN


class TestRouteDecisionService:
    def test_decide_known_route_with_policy_checks(self) -> None:
        decision = RouteDecisionService().decide("/api/live/sessions")

        assert decision.intent == Intent.LIVE_TRADING
        assert decision.confidence == 1.0
        assert "risk_governance" in decision.required_policy_checks

    def test_decide_unknown_route_uses_fallback(self) -> None:
        decision = RouteDecisionService().decide("/api/nonexistent")

        assert decision.intent == Intent.UNKNOWN
        assert decision.fallback_route == Intent.UNKNOWN
        assert decision.ambiguous is True
        assert decision.ambiguity_reason == "no_route_match"


class TestIntentRouterAgent:
    def test_dispatch_known_intent(self) -> None:
        agent = IntentRouterAgent()
        results = {}

        def handler(meta: RoutingMetadata, payload: dict | None) -> str:
            results["intent"] = meta.intent
            return "handled"

        agent.register_handler(Intent.RISK, handler)
        result = agent.dispatch("/api/risk/check")
        assert result == "handled"
        assert results["intent"] == Intent.RISK

    def test_dispatch_unknown_intent_no_fallback(self) -> None:
        agent = IntentRouterAgent()
        with pytest.raises(IntentRouterError):
            agent.dispatch("/api/nonexistent")

    def test_dispatch_unknown_intent_with_fallback(self) -> None:
        agent = IntentRouterAgent()
        fallback_called = [False]

        def fallback(meta, payload):
            fallback_called[0] = True
            return "fallback"

        agent.register_handler(Intent.UNKNOWN, fallback)
        result = agent.dispatch("/api/nonexistent")
        assert result == "fallback"
        assert fallback_called[0] is True

    def test_dispatch_no_handler_for_intent(self) -> None:
        agent = IntentRouterAgent()
        agent.register_handler(Intent.AUTH, lambda m, p: "auth")
        with pytest.raises(IntentRouterError):
            agent.dispatch("/api/risk/check")

    def test_registered_intents(self) -> None:
        agent = IntentRouterAgent()
        agent.register_handler(Intent.AUTH, lambda m, p: None)
        agent.register_handler(Intent.RISK, lambda m, p: None)
        intents = agent.registered_intents
        assert Intent.AUTH in intents
        assert Intent.RISK in intents
