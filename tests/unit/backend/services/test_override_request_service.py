from backend.common import ValidationError
from backend.services.approval import OverrideRequestDraft, OverrideRequestService


def test_override_request_service_rejects_missing_reason_or_rationale() -> None:
    service = OverrideRequestService()

    missing_reason = False
    try:
        service.validate(
            OverrideRequestDraft(
                original_decision_ref="risk_dec_001",
                original_action_ref="exec_001",
                requested_action={"type": "force_open"},
                reason_code="",
                rationale="Need emergency action",
            )
        )
    except ValidationError as exc:
        missing_reason = exc.code == "override_reason_code_required"

    missing_rationale = False
    try:
        service.validate(
            OverrideRequestDraft(
                original_decision_ref="risk_dec_001",
                original_action_ref="exec_001",
                requested_action={"type": "force_open"},
                reason_code="EMERGENCY_EXIT",
                rationale="",
            )
        )
    except ValidationError as exc:
        missing_rationale = exc.code == "override_rationale_required"

    assert missing_reason is True
    assert missing_rationale is True


def test_override_request_service_accepts_valid_draft() -> None:
    service = OverrideRequestService()

    draft = service.validate(
        OverrideRequestDraft(
            original_decision_ref="risk_dec_001",
            original_action_ref="exec_001",
            requested_action={"type": "force_exit"},
            reason_code="EMERGENCY_EXIT",
            rationale="Immediate risk containment required",
            required_roles=("RISK_MANAGER", "COMPLIANCE_OFFICER"),
        )
    )

    assert draft.reason_code == "EMERGENCY_EXIT"
