"""Registry for specialist agents available to the planner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional


@dataclass(frozen=True)
class AgentRegistration:
    """Small descriptor for one specialist entry point."""

    agent_name: str
    domain: str
    handler: Callable[..., object]


class AgentRegistry:
    """In-memory registry of specialist handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[str, AgentRegistration] = {}

    def register(self, registration: AgentRegistration) -> None:
        """Register one specialist handler by unique name."""
        if registration.agent_name in self._handlers:
            raise ValueError(f"Agent already registered: {registration.agent_name}")
        self._handlers[registration.agent_name] = registration

    def get(self, agent_name: str) -> Optional[AgentRegistration]:
        """Return a registered handler if present."""
        return self._handlers.get(agent_name)

    def list_names(self) -> Iterable[str]:
        """Return registered specialist names."""
        return tuple(sorted(self._handlers))
