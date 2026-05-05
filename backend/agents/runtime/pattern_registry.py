"""Registry for executable workflow pattern runners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from haruquant.utils import logger
from backend.contracts.workflow_plan.model import WorkflowPattern


@dataclass(frozen=True)
class WorkflowPatternRegistration:
    """One registered workflow pattern implementation."""

    pattern: WorkflowPattern
    runner: Any
    supports_concurrency: bool = False


class WorkflowPatternRegistry:
    """Mutable registry that maps workflow pattern names to runner instances."""

    def __init__(
        self,
        registrations: tuple[WorkflowPatternRegistration, ...] = (),
    ) -> None:
        self._registrations = {
            registration.pattern: registration for registration in registrations
        }

    def register(
        self,
        *,
        pattern: WorkflowPattern,
        runner: Any,
        supports_concurrency: bool = False,
    ) -> None:
        self._registrations[pattern] = WorkflowPatternRegistration(
            pattern=pattern,
            runner=runner,
            supports_concurrency=supports_concurrency,
        )

    def get(self, pattern: WorkflowPattern) -> WorkflowPatternRegistration:
        try:
            return self._registrations[pattern]
        except KeyError as exc:
            raise LookupError(f"workflow pattern not registered: {pattern.value}") from exc

    @property
    def registered_patterns(self) -> tuple[WorkflowPattern, ...]:
        return tuple(self._registrations)

