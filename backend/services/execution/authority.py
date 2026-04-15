"""Authority-state propagation helpers for execution status views."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common.logger import logger

@dataclass(frozen=True)
class AuthorityStateView:
    """Resolved authority-state badge for an execution record."""

    authority_state: str
    reason_code: str


def propagate_authority_state(
    *,
    has_receipt: bool,
    receipt_authoritative_state: str | None = None,
    reconciliation_result_state: str | None = None,
) -> AuthorityStateView:
    """Resolve the current authority-state badge for operator and audit views."""

    if reconciliation_result_state in {"CONFLICTING", "BROKER_ONLY", "LOCAL_ONLY"}:
        return AuthorityStateView(
            authority_state="RECONCILING",
            reason_code="reconciliation_pending",
        )
    if has_receipt and receipt_authoritative_state == "AUTHORITATIVE":
        return AuthorityStateView(
            authority_state="AUTHORITATIVE",
            reason_code="broker_receipt_authoritative",
        )
    return AuthorityStateView(
        authority_state="PROVISIONAL",
        reason_code="awaiting_authoritative_confirmation",
    )
