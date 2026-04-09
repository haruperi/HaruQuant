"""Approval API routes for the operator control plane."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.services.approval import (
    ApprovalCreateRequest,
    ApprovalCreationService,
    ApprovalVoteRequest,
    ApprovalVoteService,
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
