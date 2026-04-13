"""Agent circuit breaker pattern.

Tracks failure rates per agent and opens the circuit after N consecutive
failures, with exponential backoff recovery. Prevents cascade failures
when an agent is experiencing persistent issues.

State machine:
  CLOSED (normal) → OPEN (rejecting) → HALF_OPEN (testing) → CLOSED or OPEN
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit is open and calls are rejected."""

    def __init__(
        self,
        agent_name: str,
        last_failure: str,
        retry_after_seconds: float,
    ) -> None:
        self.agent_name = agent_name
        self.last_failure = last_failure
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Circuit OPEN for agent '{agent_name}': {last_failure}. "
            f"Retry after {retry_after_seconds:.1f}s"
        )


@dataclass(frozen=True)
class CircuitBreakerState:
    """Current state of a circuit breaker."""
    agent_name: str
    state: CircuitState
    failure_count: int
    last_failure_time: float
    last_failure_reason: str
    recovery_timeout: float
    last_state_change: float


class AgentCircuitBreaker:
    """Circuit breaker for agent calls.

    Prevents cascade failures by rejecting calls to failing agents
    and periodically testing recovery.

    Usage:
        cb = AgentCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        result = cb.call("strategy_agent", lambda: agent.run(...))
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        max_recovery_timeout: float = 600.0,
        backoff_multiplier: float = 2.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._max_recovery_timeout = max_recovery_timeout
        self._backoff_multiplier = backoff_multiplier
        self._circuits: Dict[str, CircuitBreakerState] = {}

    def call(
        self,
        agent_name: str,
        func: Callable[[], Any],
    ) -> Any:
        """Execute func if circuit allows, tracking success/failure.

        Raises:
            CircuitOpenError: If circuit is open and recovery not yet due.
        """
        circuit = self._get_or_create_circuit(agent_name)

        # Check if circuit is open
        if circuit.state == CircuitState.OPEN:
            elapsed = time.monotonic() - circuit.last_failure_time
            if elapsed < circuit.recovery_timeout:
                remaining = circuit.recovery_timeout - elapsed
                raise CircuitOpenError(agent_name, circuit.last_failure_reason, remaining)
            # Recovery timeout elapsed → transition to HALF_OPEN
            self._transition(agent_name, CircuitState.HALF_OPEN)
            circuit = self._circuits[agent_name]

        try:
            result = func()
            # Success → close circuit (or confirm HALF_OPEN → CLOSED)
            self._on_success(agent_name)
            return result
        except Exception as exc:
            # Failure → increment counter, potentially open circuit
            self._on_failure(agent_name, str(exc))
            raise

    def get_state(self, agent_name: str) -> Optional[CircuitBreakerState]:
        """Get current circuit state for an agent."""
        return self._circuits.get(agent_name)

    def reset(self, agent_name: str) -> None:
        """Manually reset a circuit to CLOSED state."""
        if agent_name in self._circuits:
            self._transition(agent_name, CircuitState.CLOSED)

    def reset_all(self) -> None:
        """Reset all circuits to CLOSED state."""
        for agent_name in list(self._circuits.keys()):
            self.reset(agent_name)

    def _get_or_create_circuit(self, agent_name: str) -> CircuitBreakerState:
        if agent_name not in self._circuits:
            self._circuits[agent_name] = CircuitBreakerState(
                agent_name=agent_name,
                state=CircuitState.CLOSED,
                failure_count=0,
                last_failure_time=0.0,
                last_failure_reason="",
                recovery_timeout=self._recovery_timeout,
                last_state_change=time.monotonic(),
            )
        return self._circuits[agent_name]

    def _transition(self, agent_name: str, new_state: CircuitState) -> None:
        circuit = self._circuits[agent_name]
        old_state = circuit.state
        self._circuits[agent_name] = CircuitBreakerState(
            agent_name=agent_name,
            state=new_state,
            failure_count=0 if new_state == CircuitState.CLOSED else circuit.failure_count,
            last_failure_time=circuit.last_failure_time,
            last_failure_reason=circuit.last_failure_reason,
            recovery_timeout=(
                self._recovery_timeout
                if new_state == CircuitState.CLOSED
                else min(circuit.recovery_timeout * self._backoff_multiplier, self._max_recovery_timeout)
            ),
            last_state_change=time.monotonic(),
        )

    def _on_success(self, agent_name: str) -> None:
        circuit = self._circuits.get(agent_name)
        if circuit is None:
            return
        if circuit.state == CircuitState.HALF_OPEN:
            # Successful call in HALF_OPEN → close circuit
            self._transition(agent_name, CircuitState.CLOSED)
        elif circuit.state == CircuitState.CLOSED:
            # Reset failure count on success
            if circuit.failure_count > 0:
                self._circuits[agent_name] = CircuitBreakerState(
                    agent_name=agent_name,
                    state=CircuitState.CLOSED,
                    failure_count=0,
                    last_failure_time=circuit.last_failure_time,
                    last_failure_reason=circuit.last_failure_reason,
                    recovery_timeout=self._recovery_timeout,
                    last_state_change=time.monotonic(),
                )

    def _on_failure(self, agent_name: str, reason: str) -> None:
        circuit = self._circuits.get(agent_name)
        if circuit is None:
            return

        new_failure_count = circuit.failure_count + 1
        new_state = circuit.state

        if circuit.state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN → re-open with doubled timeout
            new_state = CircuitState.OPEN
        elif new_failure_count >= self._failure_threshold:
            new_state = CircuitState.OPEN

        self._circuits[agent_name] = CircuitBreakerState(
            agent_name=agent_name,
            state=new_state,
            failure_count=new_failure_count if new_state != CircuitState.CLOSED else 0,
            last_failure_time=time.monotonic(),
            last_failure_reason=reason,
            recovery_timeout=(
                min(circuit.recovery_timeout * self._backoff_multiplier, self._max_recovery_timeout)
                if new_state != CircuitState.CLOSED
                else self._recovery_timeout
            ),
            last_state_change=time.monotonic(),
        )
