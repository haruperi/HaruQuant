"""Marginal risk evaluation helpers for hypothetical actions."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from apps.risk.core.governance_engine import GovernanceEngine
from apps.risk.core.portfolio_risk_engine import PortfolioRiskEngine
from apps.risk.core.risk_scorecard_engine import RiskScorecardEngine
from apps.risk.core.risk_snapshot_engine import RiskSnapshotEngine
from apps.risk.metrics import RiskSnapshot
from apps.risk.models import PortfolioState, PositionState
from apps.risk.scoring import RiskScorecard

from .models import RecommendationAction, RecommendationResult, RecommendationScore


def build_state_risk_engine(state: PortfolioState) -> PortfolioRiskEngine:
    """Build a portfolio risk engine backed by canonical state."""
    timeframe = str(state.metadata.get("timeframe", "H1"))
    end_pos = max(max((market.row_count for market in state.markets.values()), default=0), 1)
    return PortfolioRiskEngine(
        mt5_client=_PortfolioStateRiskAdapter(state),
        timeframe=timeframe,
        start_pos=0,
        end_pos=end_pos,
    )


def lookup_metric_value(
    snapshot: RiskSnapshot,
    metric_key: str,
    scope: str = "portfolio",
    scope_key: Optional[str] = None,
) -> Optional[float]:
    """Return one numeric metric value from a normalized snapshot."""
    for row in snapshot.metric_rows:
        if row.metric_key != metric_key or row.scope != scope:
            continue
        if scope_key is not None and row.scope_key != scope_key:
            continue
        return None if row.numeric_value is None else float(row.numeric_value)
    return None


def overall_score(scorecard: RiskScorecard) -> float:
    """Return the overall scorecard score or zero when absent."""
    value = scorecard.summary.get("overall_risk_quality_score")
    return float(value) if value is not None else 0.0


def clone_state_with_delta(
    state: PortfolioState,
    symbol: str,
    delta_lots: float,
    projected_margin_used: Optional[float] = None,
) -> PortfolioState:
    """Create a shallow cloned portfolio state with one symbol delta applied."""
    existing_positions = {position.symbol: position for position in state.positions}
    current = existing_positions.get(symbol)
    current_lots = float(current.lots) if current is not None else 0.0
    projected_lots = current_lots + float(delta_lots)

    new_positions = []
    symbols = set(existing_positions.keys()) | {symbol}
    for position_symbol in symbols:
        base_position = existing_positions.get(position_symbol)
        lots = projected_lots if position_symbol == symbol else float(base_position.lots)
        if abs(lots) < 1e-10:
            continue
        if base_position is None:
            new_positions.append(
                PositionState(
                    symbol=position_symbol,
                    lots=float(lots),
                    side="LONG" if lots >= 0 else "SHORT",
                    cluster=state.symbol_to_cluster.get(position_symbol),
                )
            )
            continue
        new_positions.append(
            replace(
                base_position,
                lots=float(lots),
                side="LONG" if lots >= 0 else "SHORT",
                cluster=base_position.cluster or state.symbol_to_cluster.get(position_symbol),
            )
        )

    new_positions.sort(key=lambda item: item.symbol)
    margin_used = projected_margin_used if projected_margin_used is not None else state.account.margin_used
    free_margin = state.account.free_margin
    if margin_used is not None:
        free_margin = float(state.account.equity) - float(margin_used)
    new_account = replace(
        state.account,
        margin_used=None if margin_used is None else float(margin_used),
        free_margin=None if free_margin is None else float(free_margin),
    )

    return replace(
        state,
        account=new_account,
        positions=new_positions,
        exposures={},
    )


class MarginalRiskEvaluator:
    """Evaluate one hypothetical action against snapshot, scorecard, and governance."""

    def __init__(
        self,
        snapshot_engine: Optional[RiskSnapshotEngine] = None,
        scorecard_engine: Optional[RiskScorecardEngine] = None,
    ):
        self.snapshot_engine = snapshot_engine or RiskSnapshotEngine()
        self.scorecard_engine = scorecard_engine or RiskScorecardEngine()

    def evaluate_action(
        self,
        state: PortfolioState,
        action: RecommendationAction,
        snapshot: Optional[RiskSnapshot] = None,
        scorecard: Optional[RiskScorecard] = None,
    ) -> RecommendationResult:
        """Evaluate a hypothetical action by rebuilding snapshot and scorecard."""
        baseline_snapshot = snapshot or self.snapshot_engine.build_snapshot(state)
        baseline_scorecard = scorecard or self.scorecard_engine.build_scorecard(baseline_snapshot)
        current_lots = float(state.position_map.get(action.symbol, 0.0))

        new_positions = dict(state.position_map)
        if abs(action.projected_lots) < 1e-10:
            new_positions.pop(action.symbol, None)
        else:
            new_positions[action.symbol] = float(action.projected_lots)

        governance_engine = GovernanceEngine(
            risk_engine=build_state_risk_engine(state),
            limits=state.limits,
        )
        governance_report = governance_engine.evaluate_transition(
            current_positions=state.position_map,
            new_positions=new_positions,
            symbol_to_cluster=state.symbol_to_cluster,
            regime=baseline_snapshot.regime_state,
            forced_decision="ACCEPT" if abs(action.projected_lots) <= abs(current_lots) else None,
            forced_reason="Candidate reduces or nets existing exposure."
            if abs(action.projected_lots) <= abs(current_lots)
            else None,
        )

        projected_state = clone_state_with_delta(
            state,
            symbol=action.symbol,
            delta_lots=action.delta_lots,
            projected_margin_used=governance_report.new_margin_used,
        )
        projected_snapshot = self.snapshot_engine.build_snapshot(projected_state)
        projected_scorecard = self.scorecard_engine.build_scorecard(projected_snapshot)

        recommendation_score = self._score_recommendation(
            baseline_snapshot=baseline_snapshot,
            baseline_scorecard=baseline_scorecard,
            projected_snapshot=projected_snapshot,
            projected_scorecard=projected_scorecard,
            governance_report=governance_report,
        )
        feasible = governance_report.decision == "ACCEPT"
        explanation = self._build_explanation(action, recommendation_score, governance_report)
        return RecommendationResult(
            action=action,
            recommendation_score=recommendation_score,
            governance_feasible=feasible,
            explanation=explanation,
            governance_report=governance_report,
            projected_snapshot=projected_snapshot,
            projected_scorecard=projected_scorecard,
            context={
                "baseline_overall_score": overall_score(baseline_scorecard),
                "projected_overall_score": overall_score(projected_scorecard),
            },
        )

    def _score_recommendation(
        self,
        baseline_snapshot: RiskSnapshot,
        baseline_scorecard: RiskScorecard,
        projected_snapshot: RiskSnapshot,
        projected_scorecard: RiskScorecard,
        governance_report,
    ) -> RecommendationScore:
        equity = max(float(baseline_snapshot.state.account.equity), 1.0)
        score_delta = overall_score(projected_scorecard) - overall_score(baseline_scorecard)
        var_delta = float(projected_snapshot.summary.get("portfolio_var", 0.0) or 0.0) - float(
            baseline_snapshot.summary.get("portfolio_var", 0.0) or 0.0
        )
        es_delta = float(projected_snapshot.summary.get("portfolio_es", 0.0) or 0.0) - float(
            baseline_snapshot.summary.get("portfolio_es", 0.0) or 0.0
        )
        scenario_delta = float(projected_snapshot.summary.get("worst_scenario_loss", 0.0) or 0.0) - float(
            baseline_snapshot.summary.get("worst_scenario_loss", 0.0) or 0.0
        )
        margin_delta = float(governance_report.new_margin_used or 0.0) - float(
            governance_report.current_margin_used or 0.0
        )

        benefit = score_delta
        benefit += max(0.0, -var_delta / equity) * 100.0
        benefit += max(0.0, -es_delta / equity) * 100.0
        benefit += max(0.0, -scenario_delta / equity) * 100.0
        benefit += max(0.0, -margin_delta / equity) * 50.0
        benefit += 5.0 if governance_report.decision == "ACCEPT" else -25.0
        return RecommendationScore(
            usefulness_score=float(benefit),
            score_delta=float(score_delta),
            var_delta=float(var_delta),
            es_delta=float(es_delta),
            worst_scenario_loss_delta=float(scenario_delta),
            margin_used_delta=float(margin_delta),
            context={
                "governance_decision": governance_report.decision,
                "governance_reason": governance_report.reason,
            },
        )

    def _build_explanation(
        self,
        action: RecommendationAction,
        recommendation_score: RecommendationScore,
        governance_report,
    ) -> str:
        return (
            f"{action.action_type} {action.symbol} by {action.delta_lots:+.4f} lots; "
            f"overall score delta={recommendation_score.score_delta:+.2f}, "
            f"VaR delta={recommendation_score.var_delta:+.2f}, "
            f"ES delta={recommendation_score.es_delta:+.2f}, "
            f"governance={governance_report.decision} ({governance_report.reason})"
        )


class _PortfolioStateRiskAdapter:
    """Minimal state-backed adapter for the shared portfolio risk engine."""

    def __init__(self, state: PortfolioState):
        self._state = state

    def get_account_equity(self):
        return float(self._state.account.equity)

    def get_peak_equity(self):
        peak_equity = self._state.metadata.get("peak_equity")
        if peak_equity is None:
            return None
        return float(peak_equity)

    def get_symbol_info(self, symbol):
        spec = self._state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        if self._state.account.margin_used is None:
            return None
        gross_lots = sum(abs(float(position.lots)) for position in self._state.positions)
        if gross_lots <= 0:
            return 0.0
        return abs(float(self._state.account.margin_used)) * (abs(float(lots)) / gross_lots)

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        market = self._state.markets.get(symbol)
        if market is None:
            return None
        bars = market.bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars
