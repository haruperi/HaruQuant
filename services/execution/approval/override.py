"""Override request skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.utils import ErrorDescriptor, ValidationError


_OVERRIDE_REASON_CODE_REQUIRED = ErrorDescriptor(
    code=4020,
    name="OVERRIDE_REASON_CODE_REQUIRED",
    message="Override request requires a reason code.",
    domain="approval",
)
_OVERRIDE_RATIONALE_REQUIRED = ErrorDescriptor(
    code=4021,
    name="OVERRIDE_RATIONALE_REQUIRED",
    message="Override request requires a written rationale.",
    domain="approval",
)


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
                _OVERRIDE_REASON_CODE_REQUIRED,
            )
        if not draft.rationale.strip():
            raise ValidationError(
                _OVERRIDE_RATIONALE_REQUIRED,
            )
        return draft
