"""Override request skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.common import ValidationError


@dataclass(frozen=True)
class OverrideRequestDraft:
    original_decision_ref: str
    original_action_ref: str
    requested_action: dict[str, object]
    reason_code: str
    rationale: str
    requested_expiry: str | None = None
    required_roles: tuple[str, ...] = field(default_factory=tuple)


class OverrideRequestService:
    """Validate override requests before later persistence wiring."""

    def validate(self, draft: OverrideRequestDraft) -> OverrideRequestDraft:
        if not draft.reason_code.strip():
            raise ValidationError(
                "override_reason_code_required",
                "Override request requires a reason code.",
            )
        if not draft.rationale.strip():
            raise ValidationError(
                "override_rationale_required",
                "Override request requires a written rationale.",
            )
        return draft
