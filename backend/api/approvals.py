"""Approval API routes for the operator control plane."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from services.utils.logger import logger
from services.execution.approval import (
    ApprovalCreateRequest,
    ApprovalCreationService,
    ApprovalVoteRequest,
    ApprovalVoteService,
    OverrideRequestDraft,
    OverrideRequestService,
)

from .auth import require_operator_role


class LiveExecutionApprovalCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_ref_id: str = Field(min_length=1)
    required_count: int = Field(gt=0)
    expires_at: str = Field(min_length=1)
    compliance_profile_id: str | None = None
    metadata_json: str = "{}"


class ApprovalVoteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(min_length=1)
    reason_code: str | None = None
    rationale: str | None = None


class OverrideApprovalCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_decision_ref: str = Field(min_length=1)
    original_action_ref: str = Field(min_length=1)
    requested_action: dict[str, object]
    reason_code: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    requested_expiry: str = Field(min_length=1)
    required_roles: tuple[str, ...] = ()


class KillSwitchRecoveryApprovalBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_ref_id: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)
    required_roles: tuple[str, ...]


router = APIRouter(prefix="/api/operator/approvals", tags=["approvals"])


def _dependencies(request: Request):
    return request.app.state.operator_dependencies


@router.post("/live-execution")
def create_live_execution_approval(
    body: LiveExecutionApprovalCreateBody,
    request: Request,
) -> dict[str, object]:
    principal = require_operator_role(request, "operator", "approver", "admin")
    approval = ApprovalCreationService(_dependencies(request).governance_repository).create(
        ApprovalCreateRequest(
            action_type="live_execution",
            target_ref_type="execution_intent",
            target_ref_id=body.target_ref_id,
            required_count=body.required_count,
            created_by_actor_type="operator",
            created_by_actor_id=principal.actor_id,
            compliance_profile_id=body.compliance_profile_id,
            expires_at=body.expires_at,
            metadata_json=body.metadata_json,
        )
    )
    return {
        "approval_id": approval.approval_id,
        "state": approval.state,
        "target_ref_id": approval.target_ref_id,
    }


@router.post("/policy-change")
def create_policy_change_approval(
    body: LiveExecutionApprovalCreateBody,
    request: Request,
) -> dict[str, object]:
    if body.required_count < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="policy change approvals require dual authorization",
        )

    principal = require_operator_role(request, "approver", "admin")
    approval = ApprovalCreationService(_dependencies(request).governance_repository).create(
        ApprovalCreateRequest(
            action_type="policy_change",
            target_ref_type="policy_version",
            target_ref_id=body.target_ref_id,
            required_count=body.required_count,
            created_by_actor_type="operator",
            created_by_actor_id=principal.actor_id,
            compliance_profile_id=body.compliance_profile_id,
            expires_at=body.expires_at,
            metadata_json=body.metadata_json,
        )
    )
    return {
        "approval_id": approval.approval_id,
        "state": approval.state,
        "target_ref_id": approval.target_ref_id,
        "required_count": approval.required_count,
    }


@router.post("/override")
def create_override_approval(
    body: OverrideApprovalCreateBody,
    request: Request,
) -> dict[str, object]:
    principal = require_operator_role(request, "operator", "approver", "admin")
    draft = OverrideRequestService().validate(
        OverrideRequestDraft(
            original_decision_ref=body.original_decision_ref,
            original_action_ref=body.original_action_ref,
            requested_action=body.requested_action,
            reason_code=body.reason_code,
            rationale=body.rationale,
            requested_expiry=body.requested_expiry,
            required_roles=body.required_roles,
        )
    )
    approval = ApprovalCreationService(_dependencies(request).governance_repository).create(
        ApprovalCreateRequest(
            action_type="override",
            target_ref_type="override_request",
            target_ref_id=draft.original_action_ref,
            required_count=max(1, len(draft.required_roles) or 1),
            created_by_actor_type="operator",
            created_by_actor_id=principal.actor_id,
            expires_at=draft.requested_expiry,
            metadata_json=body.model_dump_json(),
        )
    )
    return {
        "approval_id": approval.approval_id,
        "state": approval.state,
        "expires_at": approval.expires_at,
    }


@router.post("/kill-switch-recovery")
def create_kill_switch_recovery_approval(
    body: KillSwitchRecoveryApprovalBody,
    request: Request,
) -> dict[str, object]:
    required_roles = set(body.required_roles)
    if {"risk_manager", "compliance"} - required_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="kill switch recovery approvals require risk_manager and compliance roles",
        )

    principal = require_operator_role(request, "approver", "admin")
    approval = ApprovalCreationService(_dependencies(request).governance_repository).create(
        ApprovalCreateRequest(
            action_type="kill_switch_recovery",
            target_ref_type="kill_switch_event",
            target_ref_id=body.target_ref_id,
            required_count=2,
            created_by_actor_type="operator",
            created_by_actor_id=principal.actor_id,
            expires_at=body.expires_at,
            metadata_json=body.model_dump_json(),
        )
    )
    return {
        "approval_id": approval.approval_id,
        "state": approval.state,
        "required_count": approval.required_count,
    }


@router.post("/live-execution/{approval_id}/votes")
def vote_live_execution_approval(
    approval_id: str,
    body: ApprovalVoteBody,
    request: Request,
) -> dict[str, object]:
    principal = require_operator_role(request, "approver", "admin")
    vote = ApprovalVoteService(_dependencies(request).governance_repository).vote(
        ApprovalVoteRequest(
            approval_id=approval_id,
            approver_role=principal.role,
            approver_id=principal.actor_id,
            decision=body.decision,
            reason_code=body.reason_code,
            rationale=body.rationale,
        )
    )
    return {
        "vote_id": vote.vote_id,
        "approval_id": vote.approval_id,
        "decision": vote.decision,
    }
