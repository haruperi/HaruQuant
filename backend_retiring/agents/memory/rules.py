"""Memory write rules — defines what to remember, when, and how."""

from __future__ import annotations


class MemoryWriteRules:
    """Defines what to remember, when, and how.

    Controls which experiences get stored in long-term memory
    based on importance, outcome, and usage patterns.
    """

    @classmethod
    def should_remember_semantic(cls, content: str, importance: float) -> bool:
        """Only remember high-importance facts."""
        return importance >= 0.7 and len(content) > 10

    @classmethod
    def should_remember_episodic(cls, outcome: str, lesson: str | None) -> bool:
        """Remember failures and successes with lessons."""
        if outcome not in ("failure", "success"):
            return False
        return lesson is not None and len(lesson) > 5

    @classmethod
    def should_remember_procedural(cls, success_rate: float, usage_count: int) -> bool:
        """Only remember patterns used 3+ times with >60% success."""
        return usage_count >= 3 and success_rate >= 0.6

    @classmethod
    def compute_importance(
        cls,
        outcome: str,
        has_evidence: bool,
        is_recurring: bool,
    ) -> float:
        """Compute memory importance score (0.0-1.0)."""
        base = 0.5
        if outcome == "failure":
            base += 0.2  # Failures are more important
        elif outcome == "success":
            base += 0.1
        if has_evidence:
            base += 0.1
        if is_recurring:
            base += 0.1
        return min(1.0, base)
