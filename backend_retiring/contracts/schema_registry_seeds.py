"""Bootstrap seed records for the initial canonical schema registry."""

from __future__ import annotations

from datetime import datetime, timezone

from .schema_registry import SchemaRegistryRecord


INITIAL_EFFECTIVE_FROM = datetime(2026, 4, 8, tzinfo=timezone.utc)

INITIAL_SCHEMA_SEEDS: tuple[tuple[str, str], ...] = (
    ("WorkflowIntent", "backend_retiring.contracts.workflow_intent.model.WorkflowIntent"),
    ("WorkflowPlan", "backend_retiring.contracts.workflow_plan.model.WorkflowPlan"),
    ("TradeHypothesis", "backend_retiring.contracts.trade_hypothesis.model.TradeHypothesis"),
    ("StrategyBlueprint", "backend_retiring.contracts.strategy_blueprint.model.StrategyBlueprint"),
    ("TradeProposal", "backend_retiring.contracts.trade_proposal.model.TradeProposal"),
    ("RiskAssessmentRequest", "backend_retiring.contracts.risk_assessment_request.model.RiskAssessmentRequest"),
    ("RiskAssessmentDecision", "backend_retiring.contracts.risk_assessment_decision.model.RiskAssessmentDecision"),
    ("ExecutionIntent", "backend_retiring.contracts.execution_intent.model.ExecutionIntent"),
    ("ExecutionReceipt", "backend_retiring.contracts.execution_receipt.model.ExecutionReceipt"),
    ("ObservationEvent", "backend_retiring.contracts.observation_event.model.ObservationEvent"),
    ("EvaluationReport", "backend_retiring.contracts.evaluation_report.model.EvaluationReport"),
    ("IncidentAlert", "backend_retiring.contracts.incident_alert.model.IncidentAlert"),
    ("OverrideRequest", "backend_retiring.contracts.override_request.model.OverrideRequest"),
    ("OverrideDecision", "backend_retiring.contracts.override_decision.model.OverrideDecision"),
    ("ReplayBundle", "backend_retiring.contracts.replay_bundle.model.ReplayBundle"),
    ("RefinementReport", "backend_retiring.contracts.refinement_report.model.RefinementReport"),
    ("PageContextPacket", "backend_retiring.contracts.page_context_packet.model.PageContextPacket"),
    ("ChatLifecycleEvent", "backend_retiring.contracts.chat_lifecycle_event.model.ChatLifecycleEvent"),
)


def load_initial_schema_registry_seeds() -> list[SchemaRegistryRecord]:
    """Build the initial active registry records for canonical contracts."""

    records: list[SchemaRegistryRecord] = []
    for contract_type, model_ref in INITIAL_SCHEMA_SEEDS:
        contract_dir = contract_type.lower()
        records.append(
            SchemaRegistryRecord(
                contract_type=contract_type,
                schema_version="1.0.0",
                semantic_version="1.0.0",
                status="active",
                effective_from=INITIAL_EFFECTIVE_FROM,
                compatibility_policy="major-version compatibility",
                payload_hash=f"seed:{contract_type}:1.0.0",
                json_schema_ref=f"backend_retiring/contracts/{contract_dir}/schema.json",
                pydantic_model_ref=model_ref,
                owning_domain_team="platform",
                changelog_summary="Initial active version.",
            )
        )
    return records
