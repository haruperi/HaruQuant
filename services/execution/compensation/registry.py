"""Compensation registry mapping action classes to plans."""

from __future__ import annotations

from typing import Dict, Optional, Type

from services.utils.logger import logger
from services.execution.compensation.base import CompensationPlan


class CompensationRegistry:
    """Registry mapping action classes (A-E) to compensation plans."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[CompensationPlan]] = {}

    def register(self, action_class: str, plan_class: Type[CompensationPlan]) -> None:
        """Register a compensation plan for an action class."""
        self._registry[action_class] = plan_class
        logger.info(
            f"CompensationRegistry: registered {plan_class.__name__} "
            f"for action class {action_class}"
        )

    def get_plan(
        self, action_class: str, action_id: str
    ) -> Optional[CompensationPlan]:
        """Get a compensation plan instance for an action class."""
        plan_cls = self._registry.get(action_class)
        if plan_cls is None:
            return None
        return plan_cls(action_id)

    def has_plan(self, action_class: str) -> bool:
        return action_class in self._registry

    @property
    def registered_classes(self) -> list[str]:
        return list(self._registry.keys())


# Default registry with standard mappings
default_registry = CompensationRegistry()

# Register default compensation plans
from services.execution.compensation.order_compensation import (
    OrderCompensationPlan,
)
from services.execution.compensation.position_compensation import (
    PositionCompensationPlan,
)

default_registry.register("C", OrderCompensationPlan)
default_registry.register("D", OrderCompensationPlan)
default_registry.register("C", PositionCompensationPlan)
default_registry.register("D", PositionCompensationPlan)
default_registry.register("E", PositionCompensationPlan)
