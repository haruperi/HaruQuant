"""Risk-aware portfolio allocation service."""
from agents._shared.persistence import utc_stamp, write_json_artifact
from agents.portfolio.shared.contracts import AllocationDecision, AllocationProposal

class AllocationService:
    eligible_states = {"paper_live", "micro_live", "live", "limited_live", "normal_live"}
    def propose(self, proposal: AllocationProposal) -> AllocationDecision:
        reasons: list[str] = []
        total = sum(proposal.proposed_allocations.values())
        max_strategy = float(proposal.risk_constraints.get("max_strategy_allocation", proposal.available_capital))
        max_symbol = float(proposal.risk_constraints.get("max_symbol_allocation", proposal.available_capital))
        max_cluster = float(proposal.risk_constraints.get("max_cluster_allocation", proposal.available_capital))
        if proposal.stale:
            reasons.append("allocation_table_stale")
        if total > proposal.available_capital:
            reasons.append("total_allocation_exceeds_capital")
        for strategy_id, value in proposal.proposed_allocations.items():
            if str(proposal.lifecycle_states.get(strategy_id, "unknown")) not in self.eligible_states:
                reasons.append(f"strategy_not_eligible:{strategy_id}")
            if value > max_strategy:
                reasons.append(f"max_strategy_allocation_exceeded:{strategy_id}")
        if any(value > max_symbol for value in proposal.symbol_exposure.values()):
            reasons.append("symbol_concentration_exceeded")
        if any(value > max_cluster for value in proposal.cluster_exposure.values()):
            reasons.append("correlation_concentration_exceeded")
        result = AllocationDecision(proposal_id=proposal.proposal_id, status="rejected" if reasons else "accepted", allocations={} if reasons else proposal.proposed_allocations, constraint_report={"total_allocation": total, "available_capital": proposal.available_capital}, reasons=reasons or ["allocation_constraints_passed"], board_approval_required=proposal.board_approval_required)
        result.audit_ref = write_json_artifact("reports/logs/portfolio", f"allocation-{utc_stamp()}.json", result.model_dump() if hasattr(result, "model_dump") else result.dict())
        return result
    def equal_capital(self, strategy_ids: list[str], available_capital: float) -> dict[str, float]:
        return {} if not strategy_ids else {strategy_id: available_capital / len(strategy_ids) for strategy_id in strategy_ids}
    def confidence_weighted(self, metrics: dict[str, dict[str, float]], available_capital: float) -> dict[str, float]:
        weights = {sid: max(values.get("confidence", 0.0), 0.0) for sid, values in metrics.items()}
        total = sum(weights.values()) or 1.0
        return {sid: available_capital * weight / total for sid, weight in weights.items()}
