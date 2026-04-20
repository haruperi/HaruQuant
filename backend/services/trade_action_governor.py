"""Governed paper-execution path for AI chat action drafts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.common.ids import generate_id, generate_prefixed_id
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.serialization import canonical_json_dumps
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.data.database import (
    AiChatRepository,
    ExecutionRepository,
    GovernanceRepository,
    ProposalRepository,
    RiskRepository,
    WorkflowRepository,
)
from backend.services.ai_chat import ActionDraftRecord, ConversationService
from backend.services.execution import (
    ExecutionAttemptPersistenceService,
    ExecutionReceiptService,
    ExecutionSendService,
    SymbolMetadataCache,
    SymbolMetadataCacheEntry,
    assemble_execution_intent,
    generate_execution_idempotency_key,
    propagate_authority_state,
    run_pre_send_validation,
)
from backend.services.execution.pre_send import PreSendValidationRequest
from backend.services.safety.kill_switch import evaluate_new_entry_block
from backend.orchestration.workflow.states import KillSwitchState


UTC = timezone.utc


@dataclass(frozen=True)
class GovernorApprovalState:
    approval_id: str | None
    state: str
    approve_count: int
    reject_count: int
    required_count: int
    eligible: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class GovernedPaperExecutionResult:
    action_draft: ActionDraftRecord
    workflow_id: str
    execution_intent_id: str
    receipt_id: str
    authority_state: str
    approval_state: GovernorApprovalState
    readiness_allowed: bool
    reason_codes: tuple[str, ...]


class _PaperBrokerGateway:
    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 7001, "deal": 9001, "comment": "paper_accepted", "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 7002, "deal": 9002, "comment": "paper_modify", "request": request}

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 7003, "deal": 9003, "comment": "paper_partial_close", "request": request}

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 7004, "deal": 9004, "comment": "paper_full_close", "request": request}

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        return {"retcode": 10009, "order": 7005, "deal": 9005, "comment": "paper_cancel", "request": request}


class TradeActionGovernor:
    """Convert approved AI chat order drafts into governed paper execution."""

    def __init__(self, db_path: str, *, broker_gateway: Any | None = None) -> None:
        self.db_path = db_path
        self.chat_repository = AiChatRepository(db_path)
        self.conversation_service = ConversationService(self.chat_repository)
        self.governance_repository = GovernanceRepository(db_path)
        self.workflow_repository = WorkflowRepository(db_path)
        self.proposal_repository = ProposalRepository(db_path)
        self.risk_repository = RiskRepository(db_path)
        self.execution_repository = ExecutionRepository(db_path)
        self.broker_gateway = broker_gateway or _PaperBrokerGateway()

    def execute_paper_action_draft(
        self,
        *,
        user_id: int | str,
        draft_id: str,
        terminal_connected: bool = True,
    ) -> GovernedPaperExecutionResult:
        draft = self.conversation_service.get_action_draft(user_id=user_id, draft_id=draft_id)
        if draft.draft_type != "order_draft":
            raise ValueError("paper execution currently supports order_draft only")
        if draft.execution_intent_id and draft.execution_receipt_id:
            authority = propagate_authority_state(has_receipt=True, receipt_authoritative_state="PROVISIONAL")
            approval_state = self._evaluate_approval(draft.approval_id)
            return GovernedPaperExecutionResult(
                action_draft=draft,
                workflow_id=draft.governed_workflow_id or "",
                execution_intent_id=draft.execution_intent_id,
                receipt_id=draft.execution_receipt_id,
                authority_state=authority.authority_state,
                approval_state=approval_state,
                readiness_allowed=True,
                reason_codes=(),
            )

        approval_state = self._evaluate_approval(draft.approval_id)
        if not approval_state.eligible:
            refreshed = self.chat_repository.update_action_draft(
                draft_id=draft_id,
                user_id=str(user_id),
                status="approval_requested" if draft.approval_id else "draft",
                side_effect_status="not_executed",
                risk_precheck_notes="Paper execution blocked pending sufficient approval.",
            )
            raise PermissionError(f"paper execution blocked: {', '.join(approval_state.reason_codes) or 'approval_missing'}")

        kill_state = self._resolve_kill_switch_state(draft)
        kill_eval = evaluate_new_entry_block(kill_state)
        if kill_eval.blocked:
            self.chat_repository.update_action_draft(
                draft_id=draft_id,
                user_id=str(user_id),
                risk_precheck_status="blocked",
                risk_precheck_notes="Kill switch blocks new paper entries.",
                side_effect_status="not_executed",
            )
            raise PermissionError("paper execution blocked: kill_switch_blocks_new_entries")

        workflow_id = generate_id("workflow")
        scope_payload = {
            "action_draft_id": draft.draft_id,
            "symbol": draft.payload.get("symbol"),
            "direction": draft.payload.get("direction"),
            "thread_id": draft.thread_id,
        }
        workflow = self.workflow_repository.create_workflow(
            workflow_id=workflow_id,
            workflow_type="paper_execution",
            environment="paper",
            operating_mode="MODE-002",
            state="CREATED",
            objective=draft.title,
            scope_json=canonical_json_dumps(scope_payload),
            initiator_type="user",
            initiator_id=str(user_id),
        )
        self.workflow_repository.append_transition(
            workflow_id=workflow.workflow_id,
            from_state="CREATED",
            to_state="ACTING",
            actor_type="service",
            actor_id="trade_action_governor",
            correlation_id=generate_id("correlation"),
            phase_name="paper_execution",
            transition_reason="approved_action_draft_execution",
            metadata_json=canonical_json_dumps(scope_payload),
        )
        self.workflow_repository.update_workflow_state(
            workflow_id=workflow.workflow_id,
            expected_version=workflow.version_no,
            state="ACTING",
        )

        proposal = self._build_trade_proposal(draft=draft, workflow_id=workflow_id)
        decision = self._build_risk_decision(draft=draft, proposal=proposal, workflow_id=workflow_id)
        readiness = self._run_readiness(draft=draft, proposal=proposal, decision=decision, terminal_connected=terminal_connected)
        if not readiness.allowed:
            self.chat_repository.update_action_draft(
                draft_id=draft_id,
                user_id=str(user_id),
                status="approved",
                risk_precheck_status="blocked",
                risk_precheck_notes=f"Paper execution blocked by governor checks: {', '.join(readiness.reason_codes)}",
                governed_workflow_id=workflow_id,
                side_effect_status="not_executed",
            )
            raise PermissionError(f"paper execution blocked: {', '.join(readiness.reason_codes)}")

        idempotency_key = generate_execution_idempotency_key(
            proposal=proposal,
            risk_decision=decision,
            broker_action_type="submit_order",
            order_type="market",
        )
        intent = assemble_execution_intent(
            proposal,
            decision,
            idempotency_key=idempotency_key,
        )
        self.execution_repository.create_intent(
            execution_intent_id=intent.payload.execution_intent_id,
            workflow_id=intent.workflow_id,
            proposal_id=intent.payload.proposal_id,
            risk_decision_id=intent.payload.risk_decision_id,
            action_type=intent.payload.broker_action_type,
            symbol=intent.payload.symbol,
            side=intent.payload.side,
            order_type=intent.payload.order_type,
            size_json=canonical_json_dumps(intent.payload.size),
            price_params_json=canonical_json_dumps(intent.payload.price_params),
            sl_tp_params_json=canonical_json_dumps(intent.payload.sl_tp_params),
            idempotency_key=intent.payload.idempotency_key,
            client_order_id=generate_prefixed_id("clientexec"),
            status="PENDING_SEND",
            expiry_at=intent.payload.expiry_time.isoformat().replace("+00:00", "Z"),
            pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
        )

        send_result = ExecutionSendService(self.broker_gateway).send(intent)
        ExecutionAttemptPersistenceService(self.execution_repository).persist_attempt(
            execution_intent_id=intent.payload.execution_intent_id,
            submitted_payload=send_result.request_payload,
            transport_status="submitted",
            broker_request_ref=generate_prefixed_id("req"),
            finished_at=datetime.now(UTC).isoformat(),
            latency_ms=50,
        )
        receipt = ExecutionReceiptService(self.execution_repository).persist_receipt(
            execution_intent_id=intent.payload.execution_intent_id,
            broker_response=send_result.broker_response,
            raw_receipt_ref=f"artifact://paper-receipt/{intent.payload.execution_intent_id}",
        )
        final_intent_status = "ACKNOWLEDGED" if receipt.record.receipt_status in {"OK", "DONE", "FILLED", "ACCEPTED"} else "EXECUTION_FAILED"
        self.execution_repository.update_intent_status(
            execution_intent_id=intent.payload.execution_intent_id,
            status=final_intent_status,
            pre_send_validation_snapshot_ref=intent.payload.pre_send_validation_snapshot_ref,
        )
        self.proposal_repository.update_state(
            proposal_id=proposal.payload.proposal_id,
            state="ACKNOWLEDGED" if final_intent_status == "ACKNOWLEDGED" else "EXECUTION_FAILED",
        )
        self.chat_repository.update_action_draft(
            draft_id=draft_id,
            user_id=str(user_id),
            status="approved",
            governed_workflow_id=workflow_id,
            execution_intent_id=intent.payload.execution_intent_id,
            execution_receipt_id=receipt.record.receipt_id,
            side_effect_status="paper_execution_acknowledged" if final_intent_status == "ACKNOWLEDGED" else "paper_execution_failed",
            risk_precheck_status="passed",
            risk_precheck_notes="Paper execution completed through governed path.",
        )
        refreshed_workflow = self.workflow_repository.get_workflow(workflow_id)
        if refreshed_workflow is not None:
            self.workflow_repository.append_transition(
                workflow_id=workflow_id,
                from_state=refreshed_workflow.state,
                to_state="COMPLETED",
                actor_type="service",
                actor_id="trade_action_governor",
                correlation_id=generate_id("correlation"),
                phase_name="paper_execution",
                transition_reason="paper_execution_completed",
                metadata_json=canonical_json_dumps(
                    {
                        "execution_intent_id": intent.payload.execution_intent_id,
                        "receipt_id": receipt.record.receipt_id,
                    }
                ),
            )
            self.workflow_repository.update_workflow_state(
                workflow_id=workflow_id,
                expected_version=refreshed_workflow.version_no,
                state="COMPLETED",
                completed_at=datetime.now(UTC).isoformat(),
            )
        authority = propagate_authority_state(has_receipt=True, receipt_authoritative_state=receipt.record.authoritative_state)
        refreshed = self.conversation_service.get_action_draft(user_id=user_id, draft_id=draft_id)
        return GovernedPaperExecutionResult(
            action_draft=refreshed,
            workflow_id=workflow_id,
            execution_intent_id=intent.payload.execution_intent_id,
            receipt_id=receipt.record.receipt_id,
            authority_state=authority.authority_state,
            approval_state=approval_state,
            readiness_allowed=True,
            reason_codes=(),
        )

    def _build_trade_proposal(self, *, draft: ActionDraftRecord, workflow_id: str) -> TradeProposal:
        now = datetime.now(UTC)
        hypothesis_id = generate_id("hypothesis")
        proposal_id = generate_id("proposal")
        symbol = str(draft.payload.get("symbol") or "EURUSD")
        direction = str(draft.payload.get("direction") or "buy")
        stop_loss_logic = draft.payload.get("stop_loss_logic") or {"type": "fixed_percent", "value": 0.01}
        take_profit_logic = draft.payload.get("take_profit_logic") or {"type": "fixed_percent", "value": 0.02}
        self.proposal_repository.create_hypothesis(
            hypothesis_id=hypothesis_id,
            workflow_id=workflow_id,
            strategy_id=str(draft.payload.get("strategy_id")) if draft.payload.get("strategy_id") else None,
            symbol=symbol,
            direction=direction,
            thesis_text=draft.description,
            entry_rationale="AI chat order draft translated into governed paper execution hypothesis.",
            invalidation_rationale="Paper execution aborted if approval, kill switch, or readiness checks fail.",
            stop_loss_logic_json=canonical_json_dumps(stop_loss_logic),
            take_profit_logic_json=canonical_json_dumps(take_profit_logic),
            holding_horizon="intraday",
            confidence_score=0.65,
            calibration_note="ai_chat_phase10",
            strategy_family="ai_chat_governed_execution",
            feature_version="v1",
            strategy_code_hash="ai_chat_order_draft",
        )
        price_logic = {
            "entry_price": draft.payload.get("entry_price"),
            "entry_rationale": draft.description,
            "stop_loss_logic": stop_loss_logic,
            "take_profit_logic": take_profit_logic,
        }
        self.proposal_repository.create_proposal(
            proposal_id=proposal_id,
            workflow_id=workflow_id,
            hypothesis_id=hypothesis_id,
            state="APPROVED",
            symbol=symbol,
            direction=direction,
            candidate_price_logic_json=canonical_json_dumps(price_logic),
            proposed_size_json=canonical_json_dumps(draft.payload.get("size") or {"units": 1000}),
            transformation_version="ai_chat_phase10",
            readiness_state="ready_for_risk",
            operating_envelope_json=canonical_json_dumps({"max_slippage_bps": 5, "execution_mode": "paper"}),
            session_restrictions_json=canonical_json_dumps({"session": "paper_anytime"}),
            expiry_at=(now + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
        )
        return TradeProposal(
            workflow_id=workflow_id,
            correlation_id=generate_id("correlation"),
            causation_id=generate_id("causation"),
            timestamp_utc=now,
            originator=Originator(type="agent", id="ai_chat_supervisor"),
            environment="paper",
            operating_mode="MODE-002",
            compliance_profile_id="cmp_ai_chat_paper",
            payload=TradeProposalPayload(
                proposal_id=proposal_id,
                source_hypothesis_id=hypothesis_id,
                symbol=symbol,
                direction=direction,
                candidate_price_logic=price_logic,
                proposed_size=draft.payload.get("size") or {"units": 1000},
                operating_envelope={"max_slippage_bps": 5, "execution_mode": "paper"},
                session_restrictions={"session": "paper_anytime"},
                expiry_at=now + timedelta(minutes=15),
                transformation_version="ai_chat_phase10",
                readiness_state="ready_for_risk",
            ),
        )

    def _build_risk_decision(
        self,
        *,
        draft: ActionDraftRecord,
        proposal: TradeProposal,
        workflow_id: str,
    ) -> RiskAssessmentDecision:
        now = datetime.now(UTC)
        risk_request_id = generate_prefixed_id("riskreq")
        risk_decision_id = generate_id("risk_decision")
        self.risk_repository.create_request(
            risk_request_id=risk_request_id,
            workflow_id=workflow_id,
            proposal_id=proposal.payload.proposal_id,
            action_type="new_entry",
            strategy_lifecycle_state="PAPER_APPROVED",
            active_policy_bundle_json=canonical_json_dumps({"policy_version": "paper_policy_v1", "formula_version": "formula_v1"}),
            current_kill_switch_state="ARMED",
            account_snapshot_ref="acct_paper_ai_chat",
            portfolio_snapshot_ref="port_paper_ai_chat",
            market_snapshot_ref=f"mkt_{proposal.payload.symbol.lower()}",
            requested_freshness_json=canonical_json_dumps({"market": "fresh"}),
            compliance_profile_id="cmp_ai_chat_paper",
        )
        self.risk_repository.create_decision(
            risk_decision_id=risk_decision_id,
            risk_request_id=risk_request_id,
            proposal_id=proposal.payload.proposal_id,
            workflow_id=workflow_id,
            decision="APPROVE",
            rationale_text="Governed paper action draft passed approval and deterministic readiness prerequisites.",
            risk_metrics_snapshot_json=canonical_json_dumps({"var_95": 1.0, "max_position_units": float((draft.payload.get('size') or {'units': 1000}).get('units', 1000))}),
            freshness_expiry=(now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
            policy_version_id="paper_policy_v1",
            formula_version="formula_v1",
            provenance_bundle_id=generate_id("evidence_bundle"),
            approval_token=draft.approval_id,
            freshness_status="fresh",
        )
        return RiskAssessmentDecision(
            workflow_id=workflow_id,
            correlation_id=proposal.correlation_id,
            causation_id=generate_id("causation"),
            timestamp_utc=now,
            originator=Originator(type="service", id="risk_governor"),
            environment="paper",
            operating_mode="MODE-002",
            compliance_profile_id="cmp_ai_chat_paper",
            payload=RiskAssessmentDecisionPayload(
                risk_decision_id=risk_decision_id,
                proposal_id=proposal.payload.proposal_id,
                decision="APPROVE",
                reasons=["approval_satisfied", "paper_only_execution", "deterministic_readiness_path"],
                limit_constraints=[],
                risk_metrics_snapshot={"var_95": 1.0},
                freshness_expiry=now + timedelta(minutes=10),
                policy_version="paper_policy_v1",
                formula_version="formula_v1",
                provenance_bundle_ref=ProvenanceBundleRef(
                    bundle_id=generate_id("evidence_bundle"),
                    account_snapshot_ref="acct_paper_ai_chat",
                    market_snapshot_ref=f"mkt_{proposal.payload.symbol.lower()}",
                ),
                approval_token=draft.approval_id,
            ),
        )

    def _run_readiness(
        self,
        *,
        draft: ActionDraftRecord,
        proposal: TradeProposal,
        decision: RiskAssessmentDecision,
        terminal_connected: bool,
    ):
        metadata_cache = SymbolMetadataCache()
        metadata_cache.put(
            SymbolMetadataCacheEntry(
                snapshot_id=generate_prefixed_id("meta"),
                symbol=proposal.payload.symbol,
                observed_at=datetime.now(UTC),
                market_open=True,
                tradable=True,
                supported_fill_modes=("market",),
                stop_level_points=10,
                freeze_level_points=5,
                tick_size=0.0001,
                point_value=10.0,
                contract_size=100000.0,
                max_age_seconds=30,
            )
        )
        return run_pre_send_validation(
            PreSendValidationRequest(
                approved_proposal=proposal,
                current_proposal=proposal,
                risk_decision=decision,
                requested_fill_mode="market",
                terminal_connected=terminal_connected,
                stop_distance_points=20,
            ),
            metadata_cache=metadata_cache,
        )

    def _evaluate_approval(self, approval_id: str | None) -> GovernorApprovalState:
        if approval_id is None:
            return GovernorApprovalState(
                approval_id=None,
                state="MISSING",
                approve_count=0,
                reject_count=0,
                required_count=1,
                eligible=False,
                reason_codes=("approval_missing",),
            )
        approval = self.governance_repository.get_approval(approval_id)
        if approval is None:
            return GovernorApprovalState(
                approval_id=approval_id,
                state="MISSING",
                approve_count=0,
                reject_count=0,
                required_count=1,
                eligible=False,
                reason_codes=("approval_missing",),
            )
        votes = self.governance_repository.list_votes(approval_id)
        approve_count = sum(1 for vote in votes if vote.decision.strip().lower() == "approve")
        reject_count = sum(1 for vote in votes if vote.decision.strip().lower() == "reject")
        reason_codes: list[str] = []
        eligible = True
        if reject_count:
            eligible = False
            reason_codes.append("approval_rejected")
        if approve_count < approval.required_count:
            eligible = False
            reason_codes.append("approval_quorum_not_met")
        if approval.expires_at:
            try:
                expires_at = datetime.fromisoformat(approval.expires_at.replace("Z", "+00:00"))
                if expires_at < datetime.now(UTC):
                    eligible = False
                    reason_codes.append("approval_expired")
            except ValueError:
                pass
        return GovernorApprovalState(
            approval_id=approval_id,
            state=approval.state,
            approve_count=approve_count,
            reject_count=reject_count,
            required_count=approval.required_count,
            eligible=eligible,
            reason_codes=tuple(reason_codes),
        )

    @staticmethod
    def _resolve_kill_switch_state(draft: ActionDraftRecord) -> KillSwitchState:
        raw = str(draft.payload.get("kill_switch_state") or "ARMED").upper()
        try:
            return KillSwitchState(raw)
        except ValueError:
            return KillSwitchState.ARMED
