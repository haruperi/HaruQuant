"""Retry guard rules for uncertain execution state."""

from __future__ import annotations

from dataclasses import dataclass

from .comparison import ReconciliationComparison, ReconciliationResultState

_ACK_DELAY_STATUSES = frozenset({"SENT", "ACKNOWLEDGED"})
_BROKER_PENDING_RECEIPT_STATUSES = frozenset({"accepted", "queued", "partially_filled"})


@dataclass(frozen=True)
class RetryGuardDecision:
    allow_retry: bool
    reason_codes: tuple[str, ...]


def evaluate_retry_guard(comparison: ReconciliationComparison) -> RetryGuardDecision:
    """Fail closed when broker acknowledgement or reconciliation remains uncertain."""

    local_truth = comparison.local_truth

    if comparison.result_state is ReconciliationResultState.CONFLICTING:
        return RetryGuardDecision(
            allow_retry=False,
            reason_codes=("retry_blocked_conflicting_broker_state",),
        )

    if comparison.result_state is ReconciliationResultState.ABSENT:
        if local_truth.status in _ACK_DELAY_STATUSES:
            return RetryGuardDecision(
                allow_retry=False,
                reason_codes=("retry_blocked_ack_delay_pending_reconciliation",),
            )
        if local_truth.receipt_status in _BROKER_PENDING_RECEIPT_STATUSES:
            return RetryGuardDecision(
                allow_retry=False,
                reason_codes=("retry_blocked_pending_receipt_without_broker_truth",),
            )

    return RetryGuardDecision(
        allow_retry=True,
        reason_codes=("retry_allowed_after_reconciliation",),
    )
