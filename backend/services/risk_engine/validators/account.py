"""Account-level validators for the canonical risk state."""

from __future__ import annotations

from backend.services.risk_engine.models.account_state import AccountState
from backend.services.risk_engine.validators.common import ValidationSummary


def validate_account_state(account: AccountState) -> ValidationSummary:
    """Validate that account inputs are complete enough for risk processing."""
    summary = ValidationSummary()

    if account.equity <= 0:
        summary = summary.add(
            "error",
            "account_invalid_equity",
            "Account equity must be positive.",
            equity=account.equity,
        )

    if account.balance is not None and account.balance < 0:
        summary = summary.add(
            "warning",
            "account_negative_balance",
            "Account balance is negative.",
            balance=account.balance,
        )

    if account.margin_used is not None and account.margin_used < 0:
        summary = summary.add(
            "error",
            "account_negative_margin_used",
            "Account margin_used cannot be negative.",
            margin_used=account.margin_used,
        )

    if account.free_margin is not None and account.free_margin < 0:
        summary = summary.add(
            "warning",
            "account_negative_free_margin",
            "Account free_margin is negative.",
            free_margin=account.free_margin,
        )

    return summary
