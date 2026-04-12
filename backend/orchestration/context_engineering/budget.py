"""Context budget allocation per workflow (Playbook §9.4)."""

from __future__ import annotations

from typing import Dict, Optional


class ContextBudget:
    """Token budget allocation per workflow."""

    def __init__(
        self,
        max_tokens: int = 4096,
        per_step_budget: int = 1024,
        reserved_tokens: int = 512,
    ) -> None:
        self.max_tokens = max_tokens
        self.per_step_budget = per_step_budget
        self.reserved_tokens = reserved_tokens
        self._used = 0

    @property
    def available(self) -> int:
        return max(0, self.max_tokens - self._used - self.reserved_tokens)

    @property
    def used(self) -> int:
        return self._used

    def allocate(self, tokens: int) -> bool:
        if tokens > self.available:
            return False
        self._used += tokens
        return True

    def release(self, tokens: int) -> None:
        self._used = max(0, self._used - tokens)

    def reset(self) -> None:
        self._used = 0

    def utilization(self) -> float:
        if self.max_tokens == 0:
            return 0.0
        return self._used / self.max_tokens
