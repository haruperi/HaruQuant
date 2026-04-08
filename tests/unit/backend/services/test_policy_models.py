from backend.services.policy import (
    PolicyBundle,
    PolicyEnforcementResult,
    PolicyScope,
    PolicyVersion,
)


def test_policy_models_capture_scope_version_bundle_and_result() -> None:
    scope = PolicyScope(
        environment="paper",
        account_id="acct_001",
        strategy_id="strat_001",
        symbol="EURUSD",
        workflow_type="trade_review",
        role="TRADER",
    )
    version = PolicyVersion(
        policy_version_id="policy_001",
        policy_type="risk",
        version="1.0.0",
        status="ACTIVE",
        effective_from="2026-04-09T00:00:00Z",
        content_hash="hash_001",
    )
    bundle = PolicyBundle(
        scope=scope,
        policies=(version,),
        bundle_version="bundle_001",
        metadata={"source": "resolver"},
    )
    result = PolicyEnforcementResult(
        allowed=True,
        policy_bundle_version="bundle_001",
        reason_codes=("within_scope",),
        applied_policy_ids=("policy_001",),
        constraints={"max_size": 1000},
    )

    assert bundle.scope.symbol == "EURUSD"
    assert bundle.policies[0].policy_type == "risk"
    assert result.allowed is True
    assert result.constraints["max_size"] == 1000
