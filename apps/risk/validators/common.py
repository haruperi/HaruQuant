"""Shared validation result types for the risk subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ValidationIssue:
    """One validation issue discovered while building canonical state."""

    severity: str
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationSummary:
    """Aggregated validation result for a portfolio state."""

    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.severity == "warning" for issue in self.issues)

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        **context: Any,
    ) -> "ValidationSummary":
        return ValidationSummary(
            issues=[
                *self.issues,
                ValidationIssue(
                    severity=severity,
                    code=code,
                    message=message,
                    context=context,
                ),
            ]
        )

    def extend(self, other: "ValidationSummary") -> "ValidationSummary":
        return ValidationSummary(issues=[*self.issues, *other.issues])
