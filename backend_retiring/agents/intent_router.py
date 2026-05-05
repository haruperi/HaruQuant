"""ADK router agent for intent-based dispatch."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend_retiring.api.router import Intent, IntentClassifier, RoutingMetadata
from haruquant.utils import logger
from backend_retiring.agents.route_decision import RouteDecisionService


class IntentRouterAgent:
    """Router agent that dispatches requests to the correct workflow
    based on classified intent (Playbook §3.2, §8.1)."""

    def __init__(self, classifier: Optional[IntentClassifier] = None) -> None:
        self._classifier = classifier or IntentClassifier()
        self._route_decisions = RouteDecisionService(self._classifier)
        self._handlers: Dict[Intent, Any] = {}

    def register_handler(self, intent: Intent, handler: Any) -> None:
        """Register a handler for a specific intent."""
        self._handlers[intent] = handler

    def dispatch(
        self,
        path: str,
        *,
        priority: int = 0,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Classify intent and dispatch to the registered handler."""
        decision = self._route_decisions.decide(path)
        metadata = RoutingMetadata(
            intent=decision.intent,
            priority=priority,
            session_id=session_id,
            user_id=user_id,
        )

        if metadata.intent == Intent.UNKNOWN:
            logger.warning(
                f"IntentRouterAgent: unknown intent for '{path}', "
                f"reason={decision.ambiguity_reason}, falling back to default handler"
            )
            handler = self._handlers.get(Intent.UNKNOWN)
            if handler is None:
                raise IntentRouterError(
                    f"No handler for unknown intent: path='{path}'"
                )
        else:
            handler = self._handlers.get(metadata.intent)
            if handler is None:
                raise IntentRouterError(
                    f"No handler registered for intent={metadata.intent.value}"
                )

        logger.info(
            f"IntentRouterAgent: dispatching intent={metadata.intent.value} "
            f"path='{path}' user_id={user_id}"
        )
        return handler(metadata, payload)

    @property
    def registered_intents(self) -> list[Intent]:
        return list(self._handlers.keys())


class IntentRouterError(Exception):
    """Raised when intent routing fails."""
    pass


# Singleton instance
intent_router_agent = IntentRouterAgent()
