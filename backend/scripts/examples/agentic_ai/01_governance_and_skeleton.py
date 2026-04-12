"""Phase 1 usage examples for the agentic AI governance and skeleton foundation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import sys

from fastapi.testclient import TestClient


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.common import (  # noqa: E402
    FixedClock,
    SecretRef,
    SecretRotationPolicy,
    apply_version_update,
    evaluate_board_baseline_freshness,
    generate_prefixed_id,
    redact_secret_mapping,
    select_active_secret_version,
)
from backend.common.settings import inject_runtime_settings, load_runtime_settings_from_mapping  # noqa: E402
from backend.api import build_operator_api_dependencies, create_app  # noqa: E402
from backend.contracts import (  # noqa: E402
    SchemaRegistryService,
    load_initial_schema_registry_seeds,
    serialize_contract,
    validate_contract_payload,
)
from backend.contracts.workflow_intent.model import WorkflowIntent, WorkflowIntentPayload  # noqa: E402
from backend.contracts.workflow_plan.model import WorkflowPlan, WorkflowPlanPayload  # noqa: E402
from backend.data.database import (  # noqa: E402
    GovernanceRepository,
    ResearchAuditRepository,
    WorkflowRepository,
    apply_pending_migrations,
)
from backend.orchestration.workflow import (  # noqa: E402
    WorkflowCreateRequest,
    WorkflowCreationService,
    WorkflowState,
    WorkflowStateValidator,
    WorkflowStepRecorder,
    WorkflowStepRequest,
    WorkflowTransitionEvent,
    WorkflowTransitionLogger,
    WorkflowValidationContext,
)
from backend.services.approval import (  # noqa: E402
    ApprovalCreateRequest,
    ApprovalCreationService,
    ApprovalState,
    ApprovalStateMachine,
    ApprovalVoteRequest,
    ApprovalVoteService,
    OverrideRequestDraft,
    OverrideRequestService,
)
from backend.services.policy import (  # noqa: E402
    ApprovalPolicy,
    ComplianceProfile,
    PolicyBundle,
    PolicyResolutionQuery,
    PolicyResolver,
    PolicyScope,
    PolicyVersion,
    RetentionPolicy,
)


UTC = timezone.utc
EXAMPLE_DIR = Path(__file__).resolve().parent
TMP_DIR = EXAMPLE_DIR / "_tmp"
DB_PATH = TMP_DIR / "phase1_governance_and_skeleton.sqlite3"
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


def build_example_settings() -> object:
    settings = load_runtime_settings_from_mapping(
        {
            "app_name": "haruquant-example",
            "environment": "test",
            "api_host": "127.0.0.1",
            "api_port": 8101,
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{DB_PATH.as_posix()}",
            "event_backend": "inmemory",
            "log_level": "INFO",
            "allow_live_mutations": False,
            "mt5_enabled": False,
        }
    )
    return settings


def build_registry() -> SchemaRegistryService:
    return SchemaRegistryService(load_initial_schema_registry_seeds())


def bootstrap_database() -> tuple[WorkflowRepository, GovernanceRepository, ResearchAuditRepository]:
    applied = apply_pending_migrations(DB_PATH, MIGRATIONS_DIR)
    print(f"Applied migrations on fresh database: {len(applied)}")
    return (
        WorkflowRepository(DB_PATH),
        GovernanceRepository(DB_PATH),
        ResearchAuditRepository(DB_PATH),
    )


def example_01_runtime_settings() -> object:
    print_example_header("Example 01: Runtime Settings")
    settings = build_example_settings()
    settings_map: dict[str, object] = {}
    inject_runtime_settings(settings_map, settings)
    print(f"environment={settings.environment}")
    print(f"database_url={settings.database_url}")
    print(f"allow_live_mutations={settings.allow_live_mutations}")
    print(f"settings_keys={sorted(settings_map.keys())[:5]} ... total={len(settings_map)}")
    return settings


def example_02_core_helpers() -> None:
    print_example_header("Example 02: Core Helpers")
    correlation_id = generate_prefixed_id("corr")
    updated = apply_version_update(expected_version=1, current_version=1)
    redacted = redact_secret_mapping(
        {
            "api_key": "super-secret",
            "session_token": "super-token",
            "environment": "test",
        }
    )
    active_secret = SecretRef(
        secret_id="broker-session",
        version="v2",
        created_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
        active=True,
    )
    policy = SecretRotationPolicy(secret_id="broker-session", max_age_days=30)
    selected_secret = select_active_secret_version((active_secret,), policy=policy)
    freshness = evaluate_board_baseline_freshness(
        {
            "best_bid_ask_tick": datetime(2026, 4, 9, 9, 0, 0, tzinfo=UTC),
            "risk_decision": datetime(2026, 4, 9, 8, 59, 45, tzinfo=UTC),
            "strategy_lifecycle_state": datetime(2026, 4, 9, 8, 55, 0, tzinfo=UTC),
        },
        clock=FixedClock(datetime(2026, 4, 9, 9, 0, 1, tzinfo=UTC)),
    )
    print(f"correlation_id={correlation_id}")
    print(f"next_version={updated.current_version}")
    print(f"redacted_keys={redacted}")
    print(f"selected_secret_version={selected_secret.version}")
    print(f"freshness_valid={freshness.is_valid}")
    print(f"shortest_ttl_seconds={freshness.shortest_ttl_seconds}")


def example_03_canonical_contracts_and_registry(registry: SchemaRegistryService) -> tuple[WorkflowIntent, WorkflowPlan]:
    print_example_header("Example 03: Canonical Contracts and Schema Registry")
    workflow_id = generate_prefixed_id("wf")
    correlation_id = generate_prefixed_id("corr")
    originator = {"type": "operator", "id": "ops:example"}

    workflow_intent = WorkflowIntent(
        schema_version="1.0.0",
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        causation_id=generate_prefixed_id("cause"),
        originator=originator,
        environment="test",
        operating_mode="MODE-001",
        payload=WorkflowIntentPayload(
            objective="Review one EURUSD paper trade proposal",
            workflow_type="trade_review",
            trigger_type="user_action",
            requested_scope={"symbol": "EURUSD", "account_id": "paper-account-01"},
            constraints={"max_notional": 10000, "live_mutation": False},
            permitted_tools=["risk.snapshot.read", "policy.resolve"],
            stop_conditions=["proposal accepted", "proposal rejected"],
            timeout_policy={"seconds": 180},
            evaluation_criteria=["policy compliant", "fresh data"],
        ),
    )
    workflow_plan = WorkflowPlan(
        schema_version="1.0.0",
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        causation_id=generate_prefixed_id("cause"),
        originator=originator,
        environment="test",
        operating_mode="MODE-001",
        payload=WorkflowPlanPayload(
            plan_id=generate_prefixed_id("plan"),
            selected_pattern="sequential",
            phase_steps=[
                {"name": "observe", "contract_type": "WorkflowIntent"},
                {"name": "evaluate", "contract_type": "WorkflowPlan"},
            ],
            assigned_agents=["orchestrator", "risk_governor"],
            tool_permissions={"orchestrator": ["risk.snapshot.read"]},
            success_conditions=["risk review completed"],
            escalation_conditions=["freshness invalid"],
        ),
    )

    validated_intent = validate_contract_payload(
        json.loads(serialize_contract(workflow_intent)),
        registry,
    )
    validated_plan = validate_contract_payload(
        json.loads(serialize_contract(workflow_plan)),
        registry,
    )
    active_version = registry.get_active_version("WorkflowIntent")
    print(f"workflow_id={workflow_id}")
    print(f"validated_intent_model={validated_intent.__class__.__name__}")
    print(f"validated_plan_model={validated_plan.__class__.__name__}")
    print(f"active_workflow_intent_version={active_version.schema_version}")
    print(f"registered_contract_count={len(registry.list_versions('WorkflowIntent'))}")
    return workflow_intent, workflow_plan


def example_04_database_and_repositories(
    workflow_repo: WorkflowRepository,
    governance_repo: GovernanceRepository,
    audit_repo: ResearchAuditRepository,
) -> None:
    print_example_header("Example 04: Fresh Database and Repository Usage")
    policy = governance_repo.create_policy(
        policy_version_id=generate_prefixed_id("policy"),
        policy_type="risk_limits",
        version="2026.04.09",
        content_hash="sha256:risk-policy",
        effective_from="2026-04-09T09:00:00Z",
        status="active",
        created_by="platform",
    )
    governance_repo.create_compliance_profile(
        compliance_profile_id=generate_prefixed_id("cp"),
        name="UAE Enterprise",
        version="1.0.0",
        profile_json=json.dumps({"jurisdictions": ["AE"], "dual_auth": True}, sort_keys=True),
        active_flag=1,
    )
    kill_event = governance_repo.create_kill_switch_event(
        previous_state="ARMED",
        new_state="RECOVERY_PENDING",
        trigger_type="manual",
        reason_code="ops_review",
        actor_type="operator",
        actor_id="ops:example",
        metadata_json=json.dumps({"ticket": "INC-001"}, sort_keys=True),
    )
    evidence_bundle = audit_repo.create_evidence_bundle(
        evidence_bundle_id=generate_prefixed_id("evidence"),
        workflow_id=None,
        bundle_type="governance-review",
        summary="Initial Phase 1 evidence bundle",
        content_hash="sha256:evidence-bundle",
        freshness_status="FRESH",
    )
    legal_hold = audit_repo.place_legal_hold(
        target_type="evidence_bundle",
        target_ref_id=evidence_bundle.evidence_bundle_id,
        hold_reason="regulatory preservation",
        placed_by_actor_id="compliance:example",
    )
    print(f"policy_version_id={policy.policy_version_id}")
    print(f"kill_switch_event_id={kill_event.kill_event_id}")
    print(f"evidence_bundle_id={evidence_bundle.evidence_bundle_id}")
    print(f"active_legal_holds={len(audit_repo.list_active_legal_holds(target_type='evidence_bundle', target_ref_id=evidence_bundle.evidence_bundle_id))}")
    print(f"workflows_before_create={workflow_repo.get_workflow('missing') is None}")


def example_05_workflow_fsm_and_creation(
    workflow_repo: WorkflowRepository,
) -> str:
    print_example_header("Example 05: Workflow FSM Validation and Creation")
    validator = WorkflowStateValidator()
    validator.validate_transition(
        from_state=WorkflowState.OBSERVING,
        to_state=WorkflowState.EVALUATING,
    )
    validator.validate_transition(
        from_state=WorkflowState.EVALUATING,
        to_state=WorkflowState.COMPLETED,
        context=WorkflowValidationContext(observe_seen=True, evaluate_seen=True),
    )

    creation_service = WorkflowCreationService(workflow_repo)
    record = creation_service.create_workflow(
        WorkflowCreateRequest(
            workflow_type="trade_review",
            environment="test",
            operating_mode="MODE-001",
            objective="Review one paper-trading idea before approval",
            trigger_type="user_action",
            initiator_type="operator",
            initiator_id="ops:example",
            constraints={"max_notional": 10000, "live_mutation": False},
            permitted_tools=["risk.snapshot.read", "policy.resolve"],
            required_agents=["orchestrator", "risk_governor"],
            stop_conditions=["proposal accepted", "proposal rejected"],
            timeout_policy={"seconds": 180},
            evaluation_criteria=["policy compliant", "fresh data"],
        )
    )
    print(f"created_workflow_id={record.workflow_id}")
    print(f"created_state={record.state}")
    print(f"current_version={record.version_no}")
    return record.workflow_id


def example_06_workflow_transition_and_step_logging(
    workflow_id: str,
    workflow_repo: WorkflowRepository,
) -> None:
    print_example_header("Example 06: Workflow Transition and Step Logging")
    transition_logger = WorkflowTransitionLogger(workflow_repo)
    step_recorder = WorkflowStepRecorder(DB_PATH)
    transition_id = transition_logger.append(
        WorkflowTransitionEvent(
            workflow_id=workflow_id,
            from_state=WorkflowState.CREATED,
            to_state=WorkflowState.REASONING,
            actor_type="service",
            actor_id="workflow-engine",
            correlation_id=generate_prefixed_id("corr"),
            phase_name="reasoning",
            transition_reason="workflow started",
        )
    )
    step = step_recorder.record(
        WorkflowStepRequest(
            step_id=generate_prefixed_id("step"),
            workflow_id=workflow_id,
            step_type="observe",
            assigned_agent="orchestrator",
            input_contract_type="WorkflowIntent",
            input_ref=generate_prefixed_id("intent"),
            output_contract_type="WorkflowPlan",
            output_ref=generate_prefixed_id("plan"),
            status="completed",
            started_at="2026-04-09T09:00:00Z",
            completed_at="2026-04-09T09:00:01Z",
            latency_ms=950,
            metadata_json=json.dumps({"tool": "risk.snapshot.read"}, sort_keys=True),
        )
    )
    updated = workflow_repo.update_workflow_state(
        workflow_id=workflow_id,
        expected_version=1,
        state=WorkflowState.REASONING.value,
        current_step_id=step.step_id,
    )
    print(f"transition_row_id={transition_id}")
    print(f"recorded_step_id={step.step_id}")
    print(f"workflow_state_after_update={updated.state}")
    print(f"workflow_version_after_update={updated.version_no}")


def build_policy_bundle() -> PolicyBundle:
    return PolicyBundle(
        scope=PolicyScope(environment="test", workflow_type="trade_review", role="operator"),
        policies=(
            PolicyVersion(
                policy_version_id="policy-risk-2026-04-09",
                policy_type="risk_limits",
                version="2026.04.09",
                status="active",
                effective_from="2026-04-09T09:00:00Z",
                content_hash="sha256:risk-limits",
            ),
            PolicyVersion(
                policy_version_id="policy-approval-2026-04-09",
                policy_type="approval_controls",
                version="2026.04.09",
                status="active",
                effective_from="2026-04-09T09:00:00Z",
                content_hash="sha256:approval-controls",
            ),
        ),
        bundle_version="bundle-2026.04.09",
        metadata={"formula_version": "risk-formula-v1"},
    )


def build_compliance_profile() -> ComplianceProfile:
    return ComplianceProfile(
        compliance_profile_id="uae-enterprise-v1",
        name="UAE Enterprise",
        version="1.0.0",
        active=True,
        jurisdictions=("AE",),
        retention=RetentionPolicy(
            hot_days=30,
            archive_days=365,
            replay_retention_days=365,
            legal_hold_blocks_purge=True,
        ),
        approvals=ApprovalPolicy(
            dual_auth_live_override=True,
            hard_kill_recovery_dual_auth=True,
            policy_change_dual_auth=True,
            required_roles=("risk_manager", "compliance"),
        ),
        metadata={"profile_owner": "compliance-team"},
    )


def example_07_policy_and_compliance_resolution() -> tuple[PolicyBundle, ComplianceProfile]:
    print_example_header("Example 07: Policy Resolution and Compliance Profile")
    bundle = build_policy_bundle()
    compliance_profile = build_compliance_profile()
    resolver = PolicyResolver((bundle,))
    resolved = resolver.resolve(
        PolicyResolutionQuery(
            environment="test",
            workflow_type="trade_review",
            role="operator",
        )
    )
    print(f"resolved_bundle_version={resolved.bundle_version if resolved else 'missing'}")
    print(f"resolved_policy_count={len(resolved.policies) if resolved else 0}")
    print(f"compliance_profile={compliance_profile.name} active={compliance_profile.active}")
    print(f"required_roles={compliance_profile.approvals.required_roles}")
    return bundle, compliance_profile


def example_08_approval_and_override_usage(
    governance_repo: GovernanceRepository,
    compliance_profile: ComplianceProfile,
) -> str:
    print_example_header("Example 08: Approval and Override Services")
    creation_service = ApprovalCreationService(governance_repo)
    vote_service = ApprovalVoteService(governance_repo)
    state_machine = ApprovalStateMachine()
    override_service = OverrideRequestService()

    approval = creation_service.create(
        ApprovalCreateRequest(
            action_type="approve_trade_review",
            target_ref_type="workflow",
            target_ref_id=generate_prefixed_id("wf"),
            required_count=2,
            created_by_actor_type="operator",
            created_by_actor_id="ops:example",
            compliance_profile_id=compliance_profile.compliance_profile_id,
            expires_at=(datetime.now(UTC) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            metadata_json=json.dumps({"channel": "operator-ui"}, sort_keys=True),
        )
    )
    first_vote = vote_service.vote(
        ApprovalVoteRequest(
            approval_id=approval.approval_id,
            approver_role="risk_manager",
            approver_id="risk:alice",
            decision="APPROVE",
            rationale="Risk checks complete.",
        )
    )
    second_vote = vote_service.vote(
        ApprovalVoteRequest(
            approval_id=approval.approval_id,
            approver_role="compliance",
            approver_id="compliance:bob",
            decision="APPROVE",
            rationale="Compliance checks complete.",
        )
    )
    state_machine.validate(ApprovalState.PENDING, ApprovalState.PARTIALLY_APPROVED)
    state_machine.validate(ApprovalState.PARTIALLY_APPROVED, ApprovalState.APPROVED)
    override_draft = override_service.validate(
        OverrideRequestDraft(
            original_decision_ref="risk_decision:risk_001",
            original_action_ref="execution_intent:exec_001",
            requested_action={"action": "allow_live_exit_only"},
            reason_code="emergency_exit",
            rationale="Allow supervised exit despite manual review delay.",
            requested_expiry=(datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
            required_roles=("risk_manager", "compliance"),
        )
    )
    print(f"approval_id={approval.approval_id}")
    print(f"approval_required_count={approval.required_count}")
    print(f"vote_ids={[first_vote.vote_id, second_vote.vote_id]}")
    print(f"override_reason_code={override_draft.reason_code}")
    return approval.approval_id


def example_09_operator_api_boot(settings: object) -> None:
    print_example_header("Example 09: Operator API Boot Smoke")
    dependencies = build_operator_api_dependencies(settings=settings)
    app = create_app(dependencies)
    with TestClient(app) as client:
        health = client.get("/api/operator/health")
        metadata = client.get(
            "/api/operator",
            headers={
                "Authorization": "Bearer example-token",
                "X-HQ-Role": "operator",
                "X-HQ-Actor-Id": "ops:example",
            },
        )
    print(f"health_status={health.status_code} -> {health.json()['status']}")
    print(f"metadata_status={metadata.status_code}")
    print(f"metadata_contract_count={metadata.json()['schema_registry_contracts']}")
    print(f"metadata_actor_id={metadata.json()['actor_id']}")


if __name__ == "__main__":
    reset_example_state()
    runtime_settings = example_01_runtime_settings()
    example_02_core_helpers()
    registry_service = build_registry()
    example_03_canonical_contracts_and_registry(registry_service)
    workflow_repository, governance_repository, audit_repository = bootstrap_database()
    example_04_database_and_repositories(
        workflow_repository,
        governance_repository,
        audit_repository,
    )
    created_workflow_id = example_05_workflow_fsm_and_creation(workflow_repository)
    example_06_workflow_transition_and_step_logging(
        created_workflow_id,
        workflow_repository,
    )
    _, resolved_compliance_profile = example_07_policy_and_compliance_resolution()
    example_08_approval_and_override_usage(
        governance_repository,
        resolved_compliance_profile,
    )
    example_09_operator_api_boot(runtime_settings)
