from __future__ import annotations

import pytest

from backend_retiring.mcp import MCPServiceAuthError, MCPServiceAuthorizer


def test_mcp_service_authorizer_accepts_allowlisted_service_with_valid_token() -> None:
    authorizer = MCPServiceAuthorizer(
        shared_secret="shared-secret",
        allowed_service_ids=("workflow_orchestrator", "execution_service"),
    )

    principal = authorizer.authorize(
        service_id="workflow_orchestrator",
        bearer_token="shared-secret",
    )

    assert principal.service_id == "workflow_orchestrator"


def test_mcp_service_authorizer_rejects_invalid_token_or_unknown_service() -> None:
    authorizer = MCPServiceAuthorizer(
        shared_secret="shared-secret",
        allowed_service_ids=("workflow_orchestrator",),
    )

    with pytest.raises(MCPServiceAuthError, match="invalid service token"):
        authorizer.authorize(
            service_id="workflow_orchestrator",
            bearer_token="wrong-secret",
        )

    with pytest.raises(MCPServiceAuthError, match="not authorized"):
        authorizer.authorize(
            service_id="unknown_service",
            bearer_token="shared-secret",
        )
