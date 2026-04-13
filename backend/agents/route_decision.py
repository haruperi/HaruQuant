"""Structured route-decision service for agentic workflow dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from backend.api.router import Intent, IntentClassifier


@dataclass(frozen=True)
class RouteDecision:
    """Inspectable routing decision with fallback and confidence metadata."""

    path: str
    intent: Intent
    confidence: float
    matched_rules: tuple[str, ...]
    fallback_route: Intent | None = None
    ambiguity_reason: str | None = None
    required_policy_checks: tuple[str, ...] = ()

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_reason is not None or self.confidence < 0.5


class RouteDecisionService:
    """Classify request paths into route decisions with explicit fallback metadata."""

    def __init__(self, classifier: IntentClassifier | None = None) -> None:
        self._classifier = classifier or IntentClassifier()

    def decide(
        self,
        path: str,
        *,
        fallback_route: Intent | None = Intent.UNKNOWN,
    ) -> RouteDecision:
        route_map = self._classifier.route_map
        matches = tuple(prefix for prefix in route_map if path.startswith(prefix))
        if not matches:
            return RouteDecision(
                path=path,
                intent=Intent.UNKNOWN,
                confidence=0.0,
                matched_rules=(),
                fallback_route=fallback_route,
                ambiguity_reason="no_route_match",
                required_policy_checks=("default_deny_or_fallback",),
            )

        # Prefer the most specific prefix and mark same-length collisions ambiguous.
        max_len = max(len(match) for match in matches)
        most_specific = tuple(match for match in matches if len(match) == max_len)
        selected = sorted(most_specific)[0]
        intent = route_map[selected]
        ambiguous = len({route_map[match] for match in most_specific}) > 1
        return RouteDecision(
            path=path,
            intent=intent,
            confidence=0.6 if ambiguous else 1.0,
            matched_rules=matches,
            fallback_route=fallback_route if ambiguous else None,
            ambiguity_reason="multiple_equally_specific_routes" if ambiguous else None,
            required_policy_checks=_policy_checks_for_intent(intent),
        )


def _policy_checks_for_intent(intent: Intent) -> tuple[str, ...]:
    if intent in {Intent.EXECUTION, Intent.LIVE_TRADING}:
        return ("authz", "operating_mode", "risk_governance", "approval")
    if intent in {Intent.RESEARCH, Intent.MARKET_DATA, Intent.BACKTEST, Intent.OPTIMIZATION}:
        return ("authz", "data_access")
    if intent is Intent.RISK:
        return ("authz", "risk_policy")
    return ("authz",)

