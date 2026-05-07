"""Governed strategy lifecycle transition service."""
from agents._shared.persistence import utc_stamp, write_json_artifact
from agents.portfolio.shared.contracts import LifecycleTransitionRequest, LifecycleTransitionResult, StrategyLifecycleState

class LifecycleService:
    allowed_next = {
        StrategyLifecycleState.IDEA: {StrategyLifecycleState.SPEC, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.SPEC: {StrategyLifecycleState.CODED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.CODED: {StrategyLifecycleState.REVIEWED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.REVIEWED: {StrategyLifecycleState.BACKTESTED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.BACKTESTED: {StrategyLifecycleState.DIAGNOSED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.DIAGNOSED: {StrategyLifecycleState.OPTIMIZED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.OPTIMIZED: {StrategyLifecycleState.ROBUSTNESS_TESTED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.ROBUSTNESS_TESTED: {StrategyLifecycleState.STATISTICALLY_VALIDATED, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.STATISTICALLY_VALIDATED: {StrategyLifecycleState.PAPER_CANDIDATE, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.PAPER_CANDIDATE: {StrategyLifecycleState.PAPER_LIVE, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.PAPER_LIVE: {StrategyLifecycleState.MICRO_LIVE_CANDIDATE, StrategyLifecycleState.PAUSED, StrategyLifecycleState.RETIRED},
        StrategyLifecycleState.MICRO_LIVE_CANDIDATE: {StrategyLifecycleState.MICRO_LIVE, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.MICRO_LIVE: {StrategyLifecycleState.LIVE_CANDIDATE, StrategyLifecycleState.PAUSED, StrategyLifecycleState.RETIRED},
        StrategyLifecycleState.LIVE_CANDIDATE: {StrategyLifecycleState.LIVE, StrategyLifecycleState.REJECTED},
        StrategyLifecycleState.LIVE: {StrategyLifecycleState.PAUSED, StrategyLifecycleState.RETIRED},
        StrategyLifecycleState.PAUSED: {StrategyLifecycleState.PAPER_LIVE, StrategyLifecycleState.MICRO_LIVE, StrategyLifecycleState.LIVE, StrategyLifecycleState.RETIRED},
    }
    def transition(self, request: LifecycleTransitionRequest) -> LifecycleTransitionResult:
        reasons = []
        if request.new_state not in self.allowed_next.get(request.old_state, set()):
            reasons.append("invalid_lifecycle_transition")
        if request.new_state in {StrategyLifecycleState.MICRO_LIVE, StrategyLifecycleState.LIVE} and not request.board_approval_id:
            reasons.append("board_approval_required")
        if request.new_state in {StrategyLifecycleState.MICRO_LIVE, StrategyLifecycleState.LIVE} and not request.risk_governor_compatible:
            reasons.append("risk_governor_incompatible")
        if request.new_state == StrategyLifecycleState.PAPER_LIVE and "strategy_review" not in request.evidence_refs:
            reasons.append("strategy_review_evidence_required")
        result = LifecycleTransitionResult(transition_id=request.transition_id, strategy_id=request.strategy_id, old_state=request.old_state, new_state=request.new_state, status="rejected" if reasons else "accepted", reasons=reasons or ["transition_allowed"], evidence_refs=request.evidence_refs, actor=request.actor)
        result.audit_ref = write_json_artifact("reports/logs/portfolio", f"lifecycle-{utc_stamp()}.json", result.model_dump() if hasattr(result, "model_dump") else result.dict())
        return result
