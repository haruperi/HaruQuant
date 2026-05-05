"""Canonical contract envelope and schema registry utilities."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Literal, Mapping, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


Environment = Literal["research", "paper", "shadow", "live"]
OperatingMode = Literal["MODE-001", "MODE-002", "MODE-003"]
OriginatorType = Literal["user", "agent", "service", "tool"]
SchemaStatus = Literal["draft", "active", "deprecated", "retired"]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        text = _utc(value).isoformat().replace("+00:00", "Z")
        return text
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def canonical_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        allow_nan=False,
        default=_json_default,
        separators=(",", ":"),
        sort_keys=True,
    )


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Originator(ContractModel):
    type: OriginatorType
    id: str


class CanonicalEnvelope(ContractModel):
    schema_version: str = "1.0.0"
    contract_type: str
    workflow_id: str
    correlation_id: str
    causation_id: str
    timestamp_utc: datetime
    originator: Originator
    environment: Environment
    operating_mode: OperatingMode
    payload: Any


T = TypeVar("T", bound=BaseModel)


def serialize_contract(contract: BaseModel) -> str:
    return canonical_json_dumps(contract.model_dump(mode="json"))


def deserialize_contract(serialized: str, model_type: type[T]) -> T:
    return model_type.model_validate_json(serialized)


class SchemaRegistryRecord(ContractModel):
    contract_type: str
    schema_version: str
    semantic_version: str
    status: SchemaStatus
    effective_from: datetime
    deprecated_from: datetime | None = None
    compatibility_policy: str
    payload_hash: str
    json_schema_ref: str
    pydantic_model_ref: str
    owning_domain_team: str
    changelog_summary: str


@dataclass(frozen=True)
class SchemaRegistryRow:
    contract_type: str
    schema_version: str
    semantic_version: str
    status: str
    effective_from: str
    deprecated_from: str | None
    compatibility_policy: str
    payload_hash: str
    json_schema_ref: str
    pydantic_model_ref: str
    owning_domain_team: str
    changelog_summary: str


SCHEMA_REGISTRY_TABLE = "schema_registry"


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value).isoformat().replace("+00:00", "Z")


def record_to_row(record: SchemaRegistryRecord) -> SchemaRegistryRow:
    return SchemaRegistryRow(
        contract_type=record.contract_type,
        schema_version=record.schema_version,
        semantic_version=record.semantic_version,
        status=record.status,
        effective_from=_format_dt(record.effective_from) or "",
        deprecated_from=_format_dt(record.deprecated_from),
        compatibility_policy=record.compatibility_policy,
        payload_hash=record.payload_hash,
        json_schema_ref=record.json_schema_ref,
        pydantic_model_ref=record.pydantic_model_ref,
        owning_domain_team=record.owning_domain_team,
        changelog_summary=record.changelog_summary,
    )


def row_to_record(row: Mapping[str, Any] | SchemaRegistryRow) -> SchemaRegistryRecord:
    data = row.__dict__ if isinstance(row, SchemaRegistryRow) else dict(row)
    return SchemaRegistryRecord.model_validate(data)


class SchemaRegistryResolutionError(LookupError):
    pass


class ContractValidationError(ValueError):
    pass


class SchemaRegistryService:
    def __init__(self, records: list[SchemaRegistryRecord]) -> None:
        self._records = list(records)

    def get_version(self, contract_type: str, schema_version: str) -> SchemaRegistryRecord:
        for record in self._records:
            if (
                record.contract_type == contract_type
                and record.schema_version == schema_version
            ):
                return record
        raise SchemaRegistryResolutionError(
            f"No schema registered for {contract_type} {schema_version}"
        )

    def get_active_version(
        self,
        contract_type: str,
        *,
        at: datetime | None = None,
    ) -> SchemaRegistryRecord:
        at = _utc(at or datetime.now(timezone.utc))
        active = [
            record
            for record in self._records
            if record.contract_type == contract_type
            and record.status == "active"
            and _utc(record.effective_from) <= at
        ]
        if not active:
            raise SchemaRegistryResolutionError(
                f"No active schema registered for {contract_type}"
            )
        return sorted(active, key=lambda record: record.effective_from)[-1]

    def get_deprecated_versions(self, contract_type: str) -> list[SchemaRegistryRecord]:
        return [
            record
            for record in self._records
            if record.contract_type == contract_type and record.status == "deprecated"
        ]


INITIAL_CONTRACT_TYPES = [
    "WorkflowIntent",
    "WorkflowPlan",
    "TradeHypothesis",
    "TradeProposal",
    "RiskAssessmentRequest",
    "RiskAssessmentDecision",
    "ExecutionIntent",
    "ExecutionReceipt",
    "ObservationEvent",
    "EvaluationReport",
    "IncidentAlert",
    "OverrideRequest",
    "OverrideDecision",
    "ReplayBundle",
]

_MODULE_NAMES = {
    "WorkflowIntent": "workflow_intent",
    "WorkflowPlan": "workflow_plan",
    "TradeHypothesis": "trade_hypothesis",
    "TradeProposal": "trade_proposal",
    "RiskAssessmentRequest": "risk_assessment_request",
    "RiskAssessmentDecision": "risk_assessment_decision",
    "ExecutionIntent": "execution_intent",
    "ExecutionReceipt": "execution_receipt",
    "ObservationEvent": "observation_event",
    "EvaluationReport": "evaluation_report",
    "IncidentAlert": "incident_alert",
    "OverrideRequest": "override_request",
    "OverrideDecision": "override_decision",
    "ReplayBundle": "replay_bundle",
}

INITIAL_SCHEMA_SEEDS = [
    (
        contract_type,
        {
            "schema_version": "1.0.0",
            "semantic_version": "1.0.0",
            "status": "active",
            "effective_from": datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc),
            "compatibility_policy": "major-version compatibility",
            "payload_hash": f"sha256:{contract_type}",
            "json_schema_ref": (
                f"contracts/{_MODULE_NAMES[contract_type]}/schema.json"
            ),
            "pydantic_model_ref": (
                "contracts."
                f"{_MODULE_NAMES[contract_type]}.model.{contract_type}"
            ),
            "owning_domain_team": "platform",
            "changelog_summary": "Initial active version.",
        },
    )
    for contract_type in INITIAL_CONTRACT_TYPES
]


def load_initial_schema_registry_seeds() -> list[SchemaRegistryRecord]:
    return [
        SchemaRegistryRecord(contract_type=contract_type, **payload)
        for contract_type, payload in INITIAL_SCHEMA_SEEDS
    ]


def _load_model(model_ref: str) -> type[BaseModel]:
    module_name, class_name = model_ref.rsplit(".", 1)
    module = importlib.import_module(module_name)
    model = getattr(module, class_name)
    if not issubclass(model, BaseModel):
        raise TypeError(f"{model_ref} is not a pydantic model")
    return model


def validate_contract_payload(
    payload: Mapping[str, Any],
    registry: SchemaRegistryService,
) -> BaseModel:
    try:
        record = registry.get_version(
            str(payload.get("contract_type")),
            str(payload.get("schema_version")),
        )
        model = _load_model(record.pydantic_model_ref)
        return model.model_validate(payload)
    except (SchemaRegistryResolutionError, ValidationError, TypeError) as exc:
        raise ContractValidationError(str(exc)) from exc


class TypedEnvelope(CanonicalEnvelope):
    expected_contract_type: ClassVar[str | None] = None
    payload: Any

    @field_validator("contract_type")
    @classmethod
    def _matches_contract_type(cls, value: str) -> str:
        expected = getattr(cls, "expected_contract_type", None)
        if expected is not None and value != expected:
            raise ValueError(f"contract_type must be {expected}")
        return value


class WorkflowIntentPayload(ContractModel):
    objective: str
    workflow_type: Literal["trade_review", "research", "strategy_creation", "risk_review"]
    trigger_type: Literal["user_action", "scheduled", "system_event", "agent_request"]
    requested_scope: dict[str, Any] = Field(default_factory=dict)


class WorkflowIntent(TypedEnvelope):
    expected_contract_type = "WorkflowIntent"
    contract_type: Literal["WorkflowIntent"]
    payload: WorkflowIntentPayload


class WorkflowPattern(str, Enum):
    SEQUENTIAL = "sequential_review"
    PARALLEL = "parallel_research"
    GOVERNED = "governed_approval"


class WorkflowPhaseStep(ContractModel):
    phase: str
    owner_agent: str
    expected_output_contract_type: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowPlanPayload(ContractModel):
    plan_id: str
    selected_pattern: WorkflowPattern
    phase_steps: list[WorkflowPhaseStep] = Field(min_length=1)


class WorkflowPlan(TypedEnvelope):
    expected_contract_type = "WorkflowPlan"
    contract_type: Literal["WorkflowPlan"]
    payload: WorkflowPlanPayload


class EvidenceItem(ContractModel):
    source_type: str
    ref_id: str
    summary: str


class TradeHypothesisPayload(ContractModel):
    hypothesis_id: str
    symbol: str
    direction: Literal["buy", "sell"]
    thesis: str
    entry_rationale: str
    invalidation_rationale: str
    stop_loss_logic: dict[str, Any]
    holding_horizon: str
    confidence: float = Field(ge=0.0, le=1.0)
    calibration_note: str
    evidence: list[EvidenceItem] = Field(min_length=1)
    required_validation_data: list[str]
    strategy_family: str
    feature_version: str
    strategy_code_hash: str


class TradeHypothesis(TypedEnvelope):
    expected_contract_type = "TradeHypothesis"
    contract_type: Literal["TradeHypothesis"]
    payload: TradeHypothesisPayload


class TradeProposalPayload(ContractModel):
    proposal_id: str
    source_hypothesis_id: str
    symbol: str
    direction: Literal["buy", "sell"]
    candidate_price_logic: dict[str, Any]
    proposed_size: dict[str, Any]
    operating_envelope: dict[str, Any]
    expiry_at: datetime
    transformation_version: str
    readiness_state: Literal["draft", "ready_for_risk", "blocked"]


class TradeProposal(TypedEnvelope):
    expected_contract_type = "TradeProposal"
    contract_type: Literal["TradeProposal"]
    payload: TradeProposalPayload


class RequestedFreshnessClasses(ContractModel):
    account_snapshot: Literal["HOT", "WARM", "COLD"]
    portfolio_snapshot: Literal["HOT", "WARM", "COLD"]
    market_snapshot: Literal["HOT", "WARM", "COLD"]


class RiskAssessmentRequestPayload(ContractModel):
    risk_request_id: str
    proposal_id: str
    action_type: Literal["new_entry", "resize", "exit", "hedge"]
    requested_freshness_classes: RequestedFreshnessClasses
    account_snapshot_ref: str | None = None
    portfolio_snapshot_ref: str | None = None
    market_snapshot_ref: str | None = None
    policy_version: str


class RiskAssessmentRequest(TypedEnvelope):
    expected_contract_type = "RiskAssessmentRequest"
    contract_type: Literal["RiskAssessmentRequest"]
    payload: RiskAssessmentRequestPayload


class RiskAssessmentDecisionPayload(ContractModel):
    risk_decision_id: str
    proposal_id: str
    decision: Literal["APPROVE", "APPROVE_WITH_LIMITS", "REJECT"]
    reasons: list[str] = Field(min_length=1)
    limit_constraints: list[dict[str, Any]] = Field(default_factory=list)
    risk_metrics_snapshot: dict[str, Any]
    freshness_expiry: datetime
    policy_version: str
    formula_version: str
    provenance_bundle_ref: dict[str, Any]


class RiskAssessmentDecision(TypedEnvelope):
    expected_contract_type = "RiskAssessmentDecision"
    contract_type: Literal["RiskAssessmentDecision"]
    payload: RiskAssessmentDecisionPayload


class ExecutionIntentPayload(ContractModel):
    execution_intent_id: str
    proposal_id: str
    risk_decision_id: str
    broker_action_type: Literal["submit_order", "cancel_order", "modify_order"]
    symbol: str
    side: Literal["buy", "sell"]
    size: dict[str, Any]
    order_type: Literal["market", "limit", "stop"]
    idempotency_key: str
    expiry_time: datetime
    pre_send_validation_snapshot_ref: str


class ExecutionIntent(TypedEnvelope):
    expected_contract_type = "ExecutionIntent"
    contract_type: Literal["ExecutionIntent"]
    payload: ExecutionIntentPayload


class ExecutionReceiptPayload(ContractModel):
    receipt_id: str
    execution_intent_id: str
    broker: str
    status: Literal["accepted", "filled", "partial", "rejected", "failed"]
    authoritative_state: dict[str, Any]
    receipt_hash: str
    fill_qty: float | None = None
    fill_price: float | None = None


class ExecutionReceipt(TypedEnvelope):
    expected_contract_type = "ExecutionReceipt"
    contract_type: Literal["ExecutionReceipt"]
    payload: ExecutionReceiptPayload


class ObservationEventPayload(ContractModel):
    observation_id: str
    observation_type: str
    severity: Literal["info", "warning", "critical"]
    source: str
    payload_ref_or_inline: dict[str, Any]
    authority_state: dict[str, Any]
    freshness_status: Literal["fresh", "stale", "unknown"]
    observed_at: datetime


class ObservationEvent(TypedEnvelope):
    expected_contract_type = "ObservationEvent"
    contract_type: Literal["ObservationEvent"]
    payload: ObservationEventPayload


class EvaluationReportPayload(ContractModel):
    evaluation_id: str
    target_type: str
    target_ref: str
    rubric_name: str
    rubric_scores: dict[str, float]
    overall_score: float = Field(ge=0.0, le=1.0)
    verdict: Literal["pass", "fail", "needs_review"]
    evaluator_identity: str
    evaluation_model_id: str


class EvaluationReport(TypedEnvelope):
    expected_contract_type = "EvaluationReport"
    contract_type: Literal["EvaluationReport"]
    payload: EvaluationReportPayload


class IncidentAlertPayload(ContractModel):
    incident_id: str | None = None
    severity: Literal["info", "warning", "critical"]
    alert_type: str
    source: str
    summary: str
    incident_state: Literal["open", "acknowledged", "resolved"]
    recommended_action: str


class IncidentAlert(TypedEnvelope):
    expected_contract_type = "IncidentAlert"
    contract_type: Literal["IncidentAlert"]
    payload: IncidentAlertPayload


class OverrideRequestPayload(ContractModel):
    override_request_id: str
    original_decision_ref: str
    original_action_ref: str
    requested_action: str
    reason_code: Literal["policy_exception", "emergency_exit", "data_correction"]
    rationale: str
    requested_expiry: datetime
    required_roles: list[str] = Field(min_length=1)


class OverrideRequest(TypedEnvelope):
    expected_contract_type = "OverrideRequest"
    contract_type: Literal["OverrideRequest"]
    payload: OverrideRequestPayload


class OverrideDecisionPayload(ContractModel):
    override_decision_id: str
    override_request_id: str
    decision: Literal["approved", "rejected"]
    approver_records: list[dict[str, Any]] = Field(min_length=1)
    effective_until: datetime | None = None
    audit_ref: str


class OverrideDecision(TypedEnvelope):
    expected_contract_type = "OverrideDecision"
    contract_type: Literal["OverrideDecision"]
    payload: OverrideDecisionPayload


class IntegrityManifest(ContractModel):
    manifest_algorithm: Literal["sha256"]
    entries: list[dict[str, Any]] = Field(default_factory=list)


class ReplayBundlePayload(ContractModel):
    replay_bundle_id: str
    workflow_id: str
    completeness_status: Literal["complete", "partial", "invalid"]
    included_refs: list[str]
    export_profile: str
    generated_at: datetime
    integrity_manifest: IntegrityManifest


class ReplayBundle(TypedEnvelope):
    expected_contract_type = "ReplayBundle"
    contract_type: Literal["ReplayBundle"]
    payload: ReplayBundlePayload


class ChatLifecycleEventPayload(ContractModel):
    event_type: Literal[
        "chat.request.received",
        "chat.response.completed",
        "chat.error",
    ]
    request_id: str = Field(min_length=1)
    thread_id: str
    page_type: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ChatLifecycleEvent(TypedEnvelope):
    expected_contract_type = "ChatLifecycleEvent"
    contract_type: Literal["ChatLifecycleEvent"]
    payload: ChatLifecycleEventPayload


class EntityRef(ContractModel):
    type: str
    id: str


class ContextFreshness(ContractModel):
    observed_at: datetime
    staleness_seconds: int = Field(ge=0)


class ContextAuthority(ContractModel):
    source: str
    trust_level: Literal["authoritative", "derived", "fallback"]


class ContextSummary(ContractModel):
    headline: str
    bullets: list[str] = Field(default_factory=list)


class PageContextPayload(ContractModel):
    route: str = Field(min_length=1)
    page_type: Literal["strategy_detail", "dashboard", "risk", "generic"]
    context_revision: str
    freshness: ContextFreshness
    authority: ContextAuthority
    summary: ContextSummary
    payload: dict[str, Any]
    entity_refs: list[EntityRef] = Field(default_factory=list)


class PageContextPacket(TypedEnvelope):
    expected_contract_type = "PageContextPacket"
    contract_type: Literal["PageContextPacket"]
    payload: PageContextPayload
