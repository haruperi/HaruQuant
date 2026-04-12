"""Intent classifier and routing dispatcher for the API layer."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from backend.common.logger import logger


class Intent(str, Enum):
    """Request intent categories (Playbook §3.2)."""
    MARKET_DATA = "market_data"
    RESEARCH = "research"
    EXECUTION = "execution"
    OPTIMIZATION = "optimization"
    BACKTEST = "backtest"
    RISK = "risk"
    LIVE_TRADING = "live_trading"
    SETTINGS = "settings"
    AUTH = "auth"
    UNKNOWN = "unknown"


class RoutingMetadata:
    """Standard routing metadata attached to every request."""

    def __init__(
        self,
        intent: Intent = Intent.UNKNOWN,
        priority: int = 0,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        self.intent = intent
        self.priority = priority
        self.session_id = session_id
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "priority": self.priority,
            "session_id": self.session_id,
            "user_id": self.user_id,
        }


# Route prefix → Intent mapping table
_ROUTE_INTENT_MAP: Dict[str, Intent] = {
    "/api/strategies": Intent.RESEARCH,
    "/api/backtest": Intent.BACKTEST,
    "/api/simulator": Intent.BACKTEST,
    "/api/risk": Intent.RISK,
    "/api/live": Intent.LIVE_TRADING,
    "/api/optimization": Intent.OPTIMIZATION,
    "/api/edge-lab": Intent.RESEARCH,
    "/api/dashboard": Intent.MARKET_DATA,
    "/api/settings": Intent.SETTINGS,
    "/api/auth": Intent.AUTH,
}


class IntentClassifier:
    """Rule-based intent classifier with fallback to UNKNOWN."""

    def __init__(self) -> None:
        self._route_map = dict(_ROUTE_INTENT_MAP)

    def classify(self, path: str) -> Intent:
        """Classify request path into an Intent."""
        for prefix, intent in self._route_map.items():
            if path.startswith(prefix):
                return intent
        logger.warning(f"IntentClassifier: unknown intent for path '{path}'")
        return Intent.UNKNOWN

    def classify_and_metadata(
        self,
        path: str,
        *,
        priority: int = 0,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> RoutingMetadata:
        """Classify path and return full routing metadata."""
        intent = self.classify(path)
        return RoutingMetadata(
            intent=intent,
            priority=priority,
            session_id=session_id,
            user_id=user_id,
        )

    def add_route(self, prefix: str, intent: Intent) -> None:
        """Add or override a route mapping."""
        self._route_map[prefix] = intent

    def allowed_intents(self) -> List[Intent]:
        """Return all known intents from route map."""
        return list(set(self._route_map.values()))


# Singleton instance for middleware use
intent_classifier = IntentClassifier()
