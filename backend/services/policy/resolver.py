"""Scoped policy resolution service."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PolicyBundle, PolicyScope


@dataclass(frozen=True)
class PolicyResolutionQuery:
    """Requested policy scope."""

    environment: str
    account_id: str | None = None
    strategy_id: str | None = None
    symbol: str | None = None
    workflow_type: str | None = None
    role: str | None = None


class PolicyResolver:
    """Resolve the most specific policy bundle matching a requested scope."""

    def __init__(self, bundles: tuple[PolicyBundle, ...]) -> None:
        self.bundles = bundles

    def resolve(self, query: PolicyResolutionQuery) -> PolicyBundle | None:
        matches = [bundle for bundle in self.bundles if self._matches(bundle.scope, query)]
        if not matches:
            return None
        return max(matches, key=self._specificity)

    @staticmethod
    def _matches(scope: PolicyScope, query: PolicyResolutionQuery) -> bool:
        return (
            scope.environment == query.environment
            and (scope.account_id is None or scope.account_id == query.account_id)
            and (scope.strategy_id is None or scope.strategy_id == query.strategy_id)
            and (scope.symbol is None or scope.symbol == query.symbol)
            and (scope.workflow_type is None or scope.workflow_type == query.workflow_type)
            and (scope.role is None or scope.role == query.role)
        )

    @staticmethod
    def _specificity(bundle: PolicyBundle) -> int:
        scope = bundle.scope
        return sum(
            1
            for value in (
                scope.account_id,
                scope.strategy_id,
                scope.symbol,
                scope.workflow_type,
                scope.role,
            )
            if value is not None
        )
