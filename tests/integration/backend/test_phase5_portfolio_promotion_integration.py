from __future__ import annotations

from pathlib import Path

from backend.db import GovernanceRepository, ResearchAuditRepository, apply_pending_migrations
from backend.services import (
    EvidenceArtifact,
    EvidenceBundleStorageService,
    PromotionEvidenceValidator,
    PromotionPersistenceRequest,
    StrategyLifecycleState,
    StrategyPromotionPersistenceService,
    StrategyRegistrationRequest,
    StrategyRegistryService,
    StrategyRetirementService,
    SuspensionTriggerRequest,
    assemble_lifecycle_evidence_bundle,
    evaluate_suspension_triggers,
    route_promotion_approval,
    update_operating_envelope_for_promotion,
)


def test_phase5_strategy_promotion_path_is_evidence_backed_and_lifecycle_controlled(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    governance_repository = GovernanceRepository(database_path)
    research_repository = ResearchAuditRepository(database_path)
    with research_repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "wf_005",
                "promotion_review",
                "paper",
                "MODE-002",
                "CREATED",
                "Review lifecycle promotion for FX momentum strategy",
                "{}",
                "user",
                "operator_001",
                "{}",
                "[]",
            ),
        )

    strategy = StrategyRegistryService(governance_repository).register(
        StrategyRegistrationRequest(
            strategy_id="strat_005",
            strategy_name="FX Momentum",
            strategy_family="momentum",
            code_hash="code_hash_005",
            parameter_hash="param_hash_005",
            lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
            owner_id="owner_001",
        )
    )

    bundle = assemble_lifecycle_evidence_bundle(
        strategy_id=strategy.strategy_id,
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
        artifacts=(
            EvidenceArtifact(
                artifact_type="live_limited_report",
                artifact_ref="memory://reports/live-limited-001",
                artifact_hash="hash_live_limited_001",
            ),
        ),
    )
    stored_bundle = EvidenceBundleStorageService(research_repository).store(
        bundle,
        workflow_id="wf_005",
    )

    validation = PromotionEvidenceValidator().validate(
        target_state=StrategyLifecycleState.LIVE_LIMITED,
        evidence_bundles=(stored_bundle.record,),
    )
    approval_route = route_promotion_approval(
        target_state=StrategyLifecycleState.LIVE_LIMITED,
    )
    persistence = StrategyPromotionPersistenceService(governance_repository).persist(
        PromotionPersistenceRequest(
            strategy_id=strategy.strategy_id,
            from_state=StrategyLifecycleState.PAPER_APPROVED,
            to_state=StrategyLifecycleState.LIVE_LIMITED,
            evidence_bundle_id=stored_bundle.record.evidence_bundle_id,
            approver_1_id="risk_manager_001",
            approver_2_id="compliance_001",
            effective_at="2026-04-09T16:00:00Z",
            rationale="Promotion approved after paper trading review.",
        )
    )
    envelope = update_operating_envelope_for_promotion(
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
    )

    suspension = evaluate_suspension_triggers(
        SuspensionTriggerRequest(
            drawdown_ratio=0.25,
            unresolved_incident_count=0,
            policy_breach_count=0,
        )
    )
    retired = StrategyRetirementService(governance_repository).retire(
        strategy_id=strategy.strategy_id,
    )

    assert validation.target_state is StrategyLifecycleState.LIVE_LIMITED
    assert validation.required_bundle_types == ("live_limited_report",)
    assert approval_route.required_roles == ("risk_manager", "compliance")
    assert persistence.promotion.evidence_bundle_id == stored_bundle.record.evidence_bundle_id
    assert persistence.strategy.current_lifecycle_state == "LIVE_LIMITED"
    assert envelope.operating_mode == "MODE-003"
    assert envelope.live_trading_allowed is True
    assert envelope.approval_required is True
    assert suspension.triggered is True
    assert suspension.reason_codes == ("drawdown_threshold_breached",)
    assert retired.strategy.current_lifecycle_state == "RETIRED"
    assert retired.preserved is True
