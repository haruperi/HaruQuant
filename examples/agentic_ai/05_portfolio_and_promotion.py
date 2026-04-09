"""Phase 5 usage examples for portfolio analytics and strategy promotion."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.core import generate_prefixed_id  # noqa: E402
from backend.db import GovernanceRepository, ResearchAuditRepository, apply_pending_migrations  # noqa: E402
from backend.services.evidence import (  # noqa: E402
    EvidenceArtifact,
    EvidenceBundleStorageService,
    assemble_lifecycle_evidence_bundle,
    build_evidence_bundle_manifest,
)
from backend.services.portfolio import (  # noqa: E402
    PortfolioSnapshotAssemblyInput,
    assemble_portfolio_snapshot,
    calculate_marginal_risk_contribution,
    calculate_projected_margin_impact,
    calculate_projected_var_es_impact,
    enforce_portfolio_advisory_only,
    generate_derisk_proposal,
    generate_hedge_proposal,
    generate_rebalance_proposal,
    generate_resize_proposal,
)
from backend.services.risk import PositionExposure  # noqa: E402
from backend.services.strategy_gov import (  # noqa: E402
    PromotionEvidenceValidator,
    PromotionPersistenceRequest,
    StrategyLifecycleState,
    StrategyLifecycleTransitionValidator,
    StrategyPromotionPersistenceService,
    StrategyRegistrationRequest,
    StrategyRegistryService,
    StrategyRetirementService,
    SuspensionTriggerRequest,
    evaluate_suspension_triggers,
    route_promotion_approval,
    update_operating_envelope_for_promotion,
)


UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).resolve().parent
TMP_DIR = EXAMPLE_DIR / "_tmp" / "phase5_portfolio_and_promotion"
DB_PATH = TMP_DIR / "phase5_portfolio_and_promotion.sqlite3"
E2E_DB_PATH = TMP_DIR / "phase5_portfolio_and_promotion_e2e.sqlite3"
MIGRATIONS_DIR = Path(PROJECT_ROOT) / "backend" / "db" / "migrations"


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def reset_example_state() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_database(*, db_path: Path = DB_PATH) -> tuple[GovernanceRepository, ResearchAuditRepository]:
    applied = apply_pending_migrations(db_path, MIGRATIONS_DIR)
    print(f"Applied migrations on fresh database: {len(applied)}")
    return GovernanceRepository(db_path), ResearchAuditRepository(db_path)


def build_positions() -> tuple[PositionExposure, ...]:
    return (
        PositionExposure("EURUSD", "USD", "momentum", 45000.0, "buy"),
        PositionExposure("GBPUSD", "USD", "momentum", 25000.0, "sell"),
        PositionExposure("USDJPY", "JPY", "carry", 15000.0, "buy"),
    )


def build_evidence_artifacts(*, target_state: StrategyLifecycleState) -> tuple[EvidenceArtifact, ...]:
    artifact_type_map = {
        StrategyLifecycleState.BACKTEST_QUALIFIED: "backtest_report",
        StrategyLifecycleState.ROBUSTNESS_QUALIFIED: "robustness_report",
        StrategyLifecycleState.PAPER_APPROVED: "paper_report",
        StrategyLifecycleState.LIVE_LIMITED: "live_limited_report",
        StrategyLifecycleState.LIVE_PRODUCTION: "live_production_report",
    }
    artifact_type = artifact_type_map[target_state]
    return (
        EvidenceArtifact(
            artifact_type=artifact_type,
            artifact_ref=f"memory://evidence/{target_state.value.lower()}-report",
            artifact_hash=f"hash_{target_state.value.lower()}_001",
        ),
    )


def example_01_portfolio_analytics_service() -> None:
    print_example_header("Example 01: Portfolio Analytics Service")
    positions = build_positions()
    snapshot = assemble_portfolio_snapshot(
        PortfolioSnapshotAssemblyInput(
            portfolio_id="portfolio_phase5_001",
            observed_at=datetime(2026, 4, 9, 11, 0, tzinfo=UTC),
            positions=positions,
        ),
        snapshot_id=generate_prefixed_id("port"),
    )
    contributions = calculate_marginal_risk_contribution(positions)
    resize = generate_resize_proposal(position=positions[0], target_notional_exposure=30000.0)
    rebalance = generate_rebalance_proposal(target_allocations={"EURUSD": 0.4, "GBPUSD": 0.35, "USDJPY": 0.25})
    hedge = generate_hedge_proposal(source_position=positions[0], hedge_symbols=("USDCHF",))
    de_risk = generate_derisk_proposal(affected_symbols=("EURUSD", "GBPUSD"), target_reduction_ratio=0.25)
    projected_var = calculate_projected_var_es_impact(
        current_var=3200.0,
        current_expected_shortfall=4800.0,
        current_gross_exposure=snapshot.gross_exposure,
        target_gross_exposure=56000.0,
    )
    projected_margin = calculate_projected_margin_impact(
        balance=100000.0,
        equity=101200.0,
        free_margin=95500.0,
        margin_used=5700.0,
        projected_margin_delta=-1200.0,
    )
    advisory = enforce_portfolio_advisory_only(rebalance, requested_live_execution=False)

    print(f"portfolio_snapshot_id={snapshot.snapshot_id}")
    print(f"open_position_count={snapshot.open_position_count}")
    print(f"top_contribution={contributions[0].position_key}")
    print(f"resize_target={resize.target_size['target']}")
    print(f"rebalance_symbols={rebalance.affected_symbols}")
    print(f"hedge_symbols={hedge.hedge_symbols}")
    print(f"derisk_ratio={de_risk.target_size['reduction_ratio']}")
    print(f"projected_var={projected_var.projected_var:.2f}")
    print(f"projected_margin_utilization={projected_margin.utilization_ratio:.4f}")
    print(f"advisory_only={advisory.advisory_only}")


def example_02_strategy_registry_and_lifecycle() -> None:
    print_example_header("Example 02: Strategy Registry and Lifecycle")
    governance_repository, _ = bootstrap_database()
    registry = StrategyRegistryService(governance_repository)
    validator = StrategyLifecycleTransitionValidator()

    strategy = registry.register(
        StrategyRegistrationRequest(
            strategy_id=generate_prefixed_id("strategy"),
            strategy_name="FX Momentum Basket",
            strategy_family="momentum",
            code_hash="sha256:code-phase5",
            parameter_hash="sha256:params-phase5",
            lifecycle_state=StrategyLifecycleState.RESEARCH,
            owner_id="owner_phase5",
        )
    )
    transition = validator.validate(
        previous_state=StrategyLifecycleState.RESEARCH,
        next_state=StrategyLifecycleState.BACKTEST_QUALIFIED,
    )
    approval_route = route_promotion_approval(target_state=StrategyLifecycleState.LIVE_LIMITED)
    envelope = update_operating_envelope_for_promotion(lifecycle_state=StrategyLifecycleState.LIVE_LIMITED)
    suspension = evaluate_suspension_triggers(
        SuspensionTriggerRequest(
            drawdown_ratio=0.22,
            unresolved_incident_count=0,
            policy_breach_count=0,
        )
    )
    retired = StrategyRetirementService(governance_repository).retire(strategy_id=strategy.strategy_id)

    print(f"strategy_id={strategy.strategy_id}")
    print(f"transition={transition.previous_state.value}->{transition.next_state.value}")
    print(f"promotion_roles={approval_route.required_roles}")
    print(f"operating_mode={envelope.operating_mode}")
    print(f"suspension_triggered={suspension.triggered}")
    print(f"retired_state={retired.strategy.current_lifecycle_state}")


def example_03_evidence_bundle_automation() -> None:
    print_example_header("Example 03: Evidence Bundle Automation")
    _, research_repository = bootstrap_database()
    strategy_id = generate_prefixed_id("strategy")
    artifacts = build_evidence_artifacts(target_state=StrategyLifecycleState.LIVE_LIMITED)
    manifest = build_evidence_bundle_manifest(
        bundle_type="live_limited_report",
        strategy_id=strategy_id,
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED.value,
        artifacts=artifacts,
    )
    bundle = assemble_lifecycle_evidence_bundle(
        strategy_id=strategy_id,
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
        artifacts=artifacts,
    )
    stored = EvidenceBundleStorageService(research_repository).store(bundle)
    validation = PromotionEvidenceValidator().validate(
        target_state=StrategyLifecycleState.LIVE_LIMITED,
        evidence_bundles=(stored.record,),
    )

    print(f"manifest_artifact_count={manifest['artifact_count']}")
    print(f"bundle_type={stored.record.bundle_type}")
    print(f"evidence_bundle_id={stored.record.evidence_bundle_id}")
    print(f"content_hash_prefix={stored.content_hash[:8]}")
    print(f"validated_target_state={validation.target_state.value}")


def example_04_end_to_end_portfolio_and_promotion() -> None:
    print_example_header("Example 04: End-to-End Portfolio and Promotion")
    if E2E_DB_PATH.exists():
        E2E_DB_PATH.unlink()
    governance_repository, research_repository = bootstrap_database(db_path=E2E_DB_PATH)

    positions = build_positions()
    snapshot = assemble_portfolio_snapshot(
        PortfolioSnapshotAssemblyInput(
            portfolio_id="portfolio_phase5_e2e",
            observed_at=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            positions=positions,
        ),
        snapshot_id=generate_prefixed_id("port"),
    )
    de_risk = enforce_portfolio_advisory_only(
        generate_derisk_proposal(
            affected_symbols=("EURUSD", "GBPUSD"),
            target_reduction_ratio=0.2,
        ),
        requested_live_execution=False,
    )

    registry = StrategyRegistryService(governance_repository)
    strategy = registry.register(
        StrategyRegistrationRequest(
            strategy_id=generate_prefixed_id("strategy"),
            strategy_name="FX Momentum Promotion Path",
            strategy_family="momentum",
            code_hash="sha256:code-phase5-e2e",
            parameter_hash="sha256:params-phase5-e2e",
            lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
            owner_id="owner_phase5",
        )
    )
    artifacts = build_evidence_artifacts(target_state=StrategyLifecycleState.LIVE_LIMITED)
    bundle = assemble_lifecycle_evidence_bundle(
        strategy_id=strategy.strategy_id,
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
        artifacts=artifacts,
    )
    stored = EvidenceBundleStorageService(research_repository).store(bundle)
    validation = PromotionEvidenceValidator().validate(
        target_state=StrategyLifecycleState.LIVE_LIMITED,
        evidence_bundles=(stored.record,),
    )
    approval_route = route_promotion_approval(target_state=StrategyLifecycleState.LIVE_LIMITED)
    persistence = StrategyPromotionPersistenceService(governance_repository).persist(
        PromotionPersistenceRequest(
            strategy_id=strategy.strategy_id,
            from_state=StrategyLifecycleState.PAPER_APPROVED,
            to_state=StrategyLifecycleState.LIVE_LIMITED,
            evidence_bundle_id=stored.record.evidence_bundle_id,
            approver_1_id="risk_manager_001",
            approver_2_id="compliance_001",
            effective_at="2026-04-09T12:05:00Z",
            rationale=f"Promotion approved after advisory proposal {de_risk.action_type}.",
        )
    )
    envelope = update_operating_envelope_for_promotion(lifecycle_state=StrategyLifecycleState.LIVE_LIMITED)
    suspension = evaluate_suspension_triggers(
        SuspensionTriggerRequest(
            drawdown_ratio=0.25,
            unresolved_incident_count=0,
            policy_breach_count=0,
        )
    )
    retired = StrategyRetirementService(governance_repository).retire(strategy_id=strategy.strategy_id)

    print(f"snapshot_symbols={snapshot.symbols}")
    print(f"advisory_action={de_risk.action_type}")
    print(f"promotion_validated={validation.target_state.value}")
    print(f"promotion_roles={approval_route.required_roles}")
    print(f"promotion_state={persistence.strategy.current_lifecycle_state}")
    print(f"operating_mode={envelope.operating_mode}")
    print(f"suspension_reason_codes={suspension.reason_codes}")
    print(f"retired_state={retired.strategy.current_lifecycle_state}")


if __name__ == "__main__":
    reset_example_state()
    example_01_portfolio_analytics_service()
    example_02_strategy_registry_and_lifecycle()
    example_03_evidence_bundle_automation()
    example_04_end_to_end_portfolio_and_promotion()
