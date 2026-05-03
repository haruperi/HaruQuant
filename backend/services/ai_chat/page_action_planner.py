"""Deterministic validation and planning for registered page actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class PageActionPlanningResult:
    action_plan: dict[str, Any] | None
    summary: str
    findings: tuple[str, ...]
    evidence: tuple[str, ...]
    recommendation: str
    confidence: int
    audit_event: dict[str, Any]


class PageActionPlanner:
    """Map a user request to one registered page action and validate parameters."""

    VALID_RISK_LEVELS = {"view_only", "local_ui", "backend_non_trading", "trading_adjacent", "prohibited"}
    APP_ROUTE_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = (
        (("simulation", "simulator", "historical run", "replay"), "/simulation"),
        (("strategy creator", "strategy page", "strategies", "strategy list"), "/strategies"),
        (("optimization", "optimisation", "optimizer", "optimiser"), "/optimization"),
        (("performance", "perfomance", "performace", "perf", "backtest performance", "backtest perfomance", "performance report"), "/performance"),
        (("trades calendar", "trade calendar"), "/performance/trades-calender"),
        (("chart", "charts", "chart page", "data chart", "market chart"), "/chart"),
        (("live", "live trading", "command center"), "/live"),
        (("dashboard", "home"), "/"),
        (("operator", "operations"), "/operator"),
        (("settings", "setting"), "/settings"),
        (("documentation", "docs"), "/documentation"),
        (("tools",), "/tools"),
        (("edge lab", "edge-lab"), "/edge-lab"),
    )

    @classmethod
    def app_route_catalog(cls) -> list[dict[str, Any]]:
        """Return the app route catalog used by both deterministic and LLM planning."""
        routes: dict[str, list[str]] = {}
        for aliases, route in cls.APP_ROUTE_ALIASES:
            routes.setdefault(route, [])
            routes[route].extend(alias for alias in aliases if alias not in routes[route])
        return [
            {
                "path": route,
                "aliases": aliases,
                "label": cls._route_label(route, aliases),
            }
            for route, aliases in routes.items()
        ]

    def plan(
        self,
        *,
        user_prompt: str,
        allowed_actions: list[dict[str, Any]],
        page_type: str,
        dom_snapshot: dict[str, Any] | None = None,
    ) -> PageActionPlanningResult:
        normalized = user_prompt.lower()
        generic_action = self._generic_dom_action(allowed_actions)
        if generic_action and self._is_high_risk_generic_request(normalized):
            return self._result(
                action_plan=None,
                summary=(
                    "This requested UI action is a destructive/trading action and needs to be "
                    "registered in the common workflow actions to use it."
                ),
                findings=(
                    "The request matched destructive or trading-sensitive language.",
                    "Generic DOM operation is limited to low-risk view-only/local UI actions.",
                ),
                evidence=(f"page_type={page_type}", "source=generic_dom_safety_policy"),
                recommendation=(
                    "Register this action as an explicit common workflow action with the required "
                    "risk checks, confirmation policy, and implementation."
                ),
                confidence=100,
                status="rejected",
            )
        selected = self._select_action(normalized, allowed_actions)
        if selected is None:
            generic_parameters = self._infer_generic_dom_parameters(normalized, dom_snapshot)
            if generic_action and generic_parameters:
                selected = generic_action
                parameters = generic_parameters
            else:
                parameters = {}
        else:
            parameters = self._infer_parameters(normalized, selected, dom_snapshot)
        if selected is None:
            return self._result(
                action_plan=None,
                summary="This page does not expose a registered action for that request.",
                findings=("No allowed page action matched the user request.",),
                evidence=(f"page_type={page_type}", f"registered_actions={len(allowed_actions)}"),
                recommendation="Use one of the actions registered by the current page, or perform the action manually.",
                confidence=100,
                status="rejected",
            )

        missing = self._missing_required_parameters(selected, parameters)
        if missing:
            return self._result(
                action_plan=None,
                summary=f"The page action `{selected['id']}` needs more information before it can be planned.",
                findings=(f"Missing required parameters: {', '.join(missing)}",),
                evidence=(f"action_id={selected['id']}", f"page_type={page_type}"),
                recommendation=f"Please provide: {', '.join(missing)}.",
                confidence=92,
                status="needs_input",
            )

        risk_level = str(selected.get("riskLevel") or selected.get("risk_level") or "view_only")
        if risk_level not in self.VALID_RISK_LEVELS:
            risk_level = "prohibited"

        action_plan = {
            "action_id": selected["id"],
            "description": selected.get("description"),
            "risk_level": risk_level,
            "parameters": parameters,
            "reasoning": f"Matched user request to registered page action `{selected['id']}`.",
        }
        return self._result(
            action_plan=action_plan,
            summary=f"Prepared a registered page action plan for {selected.get('label') or selected['id']}.",
            findings=(f"Matched action `{selected['id']}`.", f"risk_level={risk_level}"),
            evidence=(f"page_type={page_type}", "source=registered_page_action"),
            recommendation="Review the action preview before execution.",
            confidence=88,
            status="planned",
        )

    @staticmethod
    def _select_action(normalized: str, allowed_actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        action_by_id = {str(action.get("id")): action for action in allowed_actions if action.get("id")}
        for action_id, action in action_by_id.items():
            if action_id.lower() in normalized:
                return action
        if "trades calendar" in normalized:
            return action_by_id.get("navigate_performance_page") or PageActionPlanner._find_by_tokens(allowed_actions, ("performance", "navigate"))
        if "strategy" not in normalized and "select" in normalized and "backtest" in normalized and any(
            token in normalized
            for token in ("second", "third", "fourth", "fifth", "2nd", "3rd", "4th", "5th", "#", " 2", " 3", " 4", " 5")
        ):
            return action_by_id.get("backtests.select_by_index") or action_by_id.get("backtests.select_first")
        if "strategy" not in normalized and (
            "first backtest" in normalized
            or ("select" in normalized and "backtest" in normalized and "first" in normalized)
        ):
            return action_by_id.get("backtests.select_first")
        if "clear" in normalized and "backtest" in normalized:
            return action_by_id.get("backtests.clear_selection")
        if ("refresh" in normalized or "reload" in normalized) and "backtest" in normalized:
            return action_by_id.get("backtests.refresh")
        if PageActionPlanner._is_navigation_request(normalized):
            return (
                action_by_id.get("navigate_app_page")
                or action_by_id.get("navigate_performance_page")
                or PageActionPlanner._find_by_tokens(allowed_actions, ("navigate",))
            )
        if "monte carlo" in normalized or "monte-carlo" in normalized:
            return action_by_id.get("switch_optimization_tab") or PageActionPlanner._find_by_tokens(allowed_actions, ("optimization", "tab"))
        if "walk forward" in normalized or "walk-forward" in normalized:
            return action_by_id.get("switch_optimization_tab")
        if "change symbol" in normalized or "switch symbol" in normalized:
            return action_by_id.get("live_trading.change_symbol")
        if "change timeframe" in normalized or "switch timeframe" in normalized:
            return action_by_id.get("live_trading.change_timeframe")
        if "export" in normalized or "download" in normalized:
            return PageActionPlanner._find_by_tokens(allowed_actions, ("export",)) or PageActionPlanner._find_by_tokens(allowed_actions, ("download",))
        if "open" in normalized or "show" in normalized or "click" in normalized:
            return PageActionPlanner._find_by_prompt_words(normalized, allowed_actions)
        return PageActionPlanner._find_by_prompt_words(normalized, allowed_actions)

    @staticmethod
    def _is_navigation_request(normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in (
                "go to",
                "open",
                "show me",
                "take me",
                "navigate",
                "switch to",
                "the path is",
                "the route is",
            )
        )

    @staticmethod
    def _find_by_tokens(allowed_actions: list[dict[str, Any]], tokens: tuple[str, ...]) -> dict[str, Any] | None:
        for action in allowed_actions:
            haystack = " ".join(str(action.get(key) or "") for key in ("id", "label", "description")).lower()
            if all(token in haystack for token in tokens):
                return action
        return None

    @staticmethod
    def _find_by_prompt_words(normalized: str, allowed_actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        prompt_words = {word for word in normalized.replace("_", " ").replace("-", " ").split() if len(word) > 3}
        best: tuple[int, dict[str, Any] | None] = (0, None)
        for action in allowed_actions:
            haystack = " ".join(str(action.get(key) or "") for key in ("id", "label", "description")).lower()
            if "strategy" in normalized and "backtest" not in normalized and "backtest" in haystack:
                continue
            if "backtest" in normalized and "strategy" not in normalized and "strategy" in haystack and "backtest" not in haystack:
                continue
            action_words = set(haystack.replace("_", " ").replace("-", " ").split())
            score = len(prompt_words & action_words)
            if score > best[0]:
                best = (score, action)
        return best[1] if best[0] > 0 else None

    @staticmethod
    def _generic_dom_action(allowed_actions: list[dict[str, Any]]) -> dict[str, Any] | None:
        for action in allowed_actions:
            if action.get("id") == "generic_dom_click":
                return action
        return None

    @staticmethod
    def _is_high_risk_generic_request(normalized: str) -> bool:
        high_risk_terms = (
            "delete",
            "remove",
            "place order",
            "buy ",
            "sell ",
            "execute trade",
            "live order",
            "start live",
            "stop live",
            "broker",
        )
        return any(term in normalized for term in high_risk_terms)

    @classmethod
    def _infer_generic_dom_parameters(cls, normalized: str, dom_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        if cls._is_high_risk_generic_request(normalized) or not isinstance(dom_snapshot, dict):
            return {}
        elements = dom_snapshot.get("actionable_elements")
        if not isinstance(elements, list):
            return {}
        target = cls._find_dom_target(normalized, elements)
        if not target:
            return {}
        selector = target.get("selector")
        label = target.get("label")
        if not isinstance(selector, str) or not selector:
            return {}
        return {
            "selector": selector,
            "label": str(label or ""),
        }

    @staticmethod
    def _find_dom_target(normalized: str, elements: list[object]) -> dict[str, Any] | None:
        prompt_words = {
            word
            for word in normalized.replace("_", " ").replace("-", " ").replace("/", " ").split()
            if len(word) > 2 and word not in {"the", "and", "this", "that", "page", "click", "select", "open", "show"}
        }
        ordinal_index = 0 if "first" in normalized else 1 if "second" in normalized else 2 if "third" in normalized else None
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for raw_index, raw in enumerate(elements):
            if not isinstance(raw, dict):
                continue
            label = str(raw.get("label") or "").lower()
            role = str(raw.get("role") or "").lower()
            if not label:
                continue
            if any(term in label for term in ("delete", "remove", "buy", "sell", "place order")):
                continue
            label_words = set(label.replace("_", " ").replace("-", " ").replace("/", " ").split())
            score = len(prompt_words & label_words) * 10
            if "row" in normalized and role in {"row", "link", "button"}:
                score += 2
            if "tab" in normalized and role == "tab":
                score += 5
            if "button" in normalized and role == "button":
                score += 3
            if score > 0:
                scored.append((score, raw_index, raw))
        if not scored:
            return None
        scored.sort(key=lambda item: (-item[0], item[1]))
        if ordinal_index is not None and ordinal_index < len(scored):
            return scored[ordinal_index][2]
        return scored[0][2]

    @staticmethod
    def _infer_parameters(normalized: str, action: dict[str, Any], dom_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        action_id = str(action.get("id") or "")
        if action_id in {"navigate_app_page", "navigate_performance_page"}:
            explicit_route = PageActionPlanner._extract_explicit_route(normalized)
            if explicit_route:
                return {"path": explicit_route}
            inferred_route = PageActionPlanner._infer_app_route(normalized)
            if inferred_route:
                if action_id == "navigate_performance_page" and inferred_route.startswith("/performance/"):
                    return {"path": inferred_route.removeprefix("/performance/")}
                return {"path": inferred_route}
            if "trades calendar" in normalized:
                return {"path": "trades-calender"}
            if "strategy analysis" in normalized:
                return {"path": "strategy-analysis"}
            if "trade analysis" in normalized:
                return {"path": "trade-analysis"}
            if "overview" in normalized:
                return {"path": "overview"}
        if action_id == "backtests.select_by_index":
            if "first" in normalized or "1st" in normalized:
                return {"index": 1}
            if "second" in normalized or "2nd" in normalized:
                return {"index": 2}
            if "third" in normalized or "3rd" in normalized:
                return {"index": 3}
            if "fourth" in normalized or "4th" in normalized:
                return {"index": 4}
            if "fifth" in normalized or "5th" in normalized:
                return {"index": 5}
            for token in normalized.replace("#", " ").split():
                if token.isdigit():
                    return {"index": int(token)}
        if action_id == "generic_dom_click":
            return PageActionPlanner._infer_generic_dom_parameters(normalized, dom_snapshot)
        if action_id == "switch_optimization_tab":
            if "monte" in normalized:
                return {"tab": "monte-carlo"}
            if "walk" in normalized:
                return {"tab": "wfa"}
            return {"tab": "optimization"}
        if action_id == "live_trading.change_symbol":
            words = normalized.upper().split()
            for word in words:
                if 5 <= len(word) <= 8 and word.isalpha():
                    return {"symbol": word}
        if action_id == "live_trading.change_timeframe":
            for token in normalized.upper().replace(",", " ").split():
                if token in {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}:
                    return {"timeframe": token}
        return {}

    @staticmethod
    def _extract_explicit_route(normalized: str) -> str | None:
        route_match = re.search(r"/[a-z0-9][a-z0-9/_-]*", normalized)
        if route_match:
            return route_match.group(0).rstrip(".,;:'\"}")
        for token in normalized.replace(",", " ").split():
            if token.startswith("/") and len(token) > 1:
                return token.rstrip(".,;:")
        return None

    @classmethod
    def _infer_app_route(cls, normalized: str) -> str | None:
        for aliases, route in cls.APP_ROUTE_ALIASES:
            if any(alias in normalized for alias in aliases):
                return route
        return None

    @classmethod
    def _infer_fuzzy_app_route(cls, normalized: str) -> tuple[str, float] | None:
        normalized_words = re.sub(r"[^a-z0-9\s/-]", " ", normalized.lower())
        best: tuple[str, float] | None = None
        for aliases, route in cls.APP_ROUTE_ALIASES:
            for alias in aliases:
                score = SequenceMatcher(None, alias, normalized_words).ratio()
                if alias in normalized_words:
                    score = 1.0
                elif len(alias.split()) == 1:
                    for word in normalized_words.split():
                        score = max(score, SequenceMatcher(None, alias, word).ratio())
                if best is None or score > best[1]:
                    best = (route, score)
        return best

    @staticmethod
    def _route_label(route: str, aliases: list[str]) -> str:
        if route == "/":
            return "Home"
        preferred = aliases[0] if aliases else route.strip("/")
        return preferred.replace("-", " ").title()

    @staticmethod
    def _missing_required_parameters(action: dict[str, Any], parameters: dict[str, Any]) -> list[str]:
        required: list[str] = []
        for parameter in action.get("parameters") or []:
            if isinstance(parameter, dict) and parameter.get("required") and parameter.get("name") not in parameters:
                required.append(str(parameter["name"]))
        input_schema = action.get("inputSchema")
        if isinstance(input_schema, dict):
            required_values = input_schema.get("required")
            if isinstance(required_values, list):
                required.extend(str(value) for value in required_values if str(value) not in parameters)
        return list(dict.fromkeys(required))

    @staticmethod
    def _result(
        *,
        action_plan: dict[str, Any] | None,
        summary: str,
        findings: tuple[str, ...],
        evidence: tuple[str, ...],
        recommendation: str,
        confidence: int,
        status: str,
    ) -> PageActionPlanningResult:
        return PageActionPlanningResult(
            action_plan=action_plan,
            summary=summary,
            findings=findings,
            evidence=evidence,
            recommendation=recommendation,
            confidence=confidence,
            audit_event={
                "event_id": f"page_action_plan_{uuid4().hex}",
                "event_type": "page_action_plan",
                "status": status,
                "action_id": action_plan.get("action_id") if action_plan else None,
                "risk_level": action_plan.get("risk_level") if action_plan else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )


__all__ = ["PageActionPlanner", "PageActionPlanningResult"]
