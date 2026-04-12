"""Simulation risk/report serialization helpers."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Dict, List, Optional

from backend.services.risk_engine.core.portfolio_risk_engine import PortfolioRiskEngine
from backend.services.risk_engine.models import PortfolioState


def _serialize_limit_events(events: Optional[List[Any]]) -> list[dict]:
    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
        return value

    output: list[dict] = []
    for event in events or []:
        output.append(
            {
                "rule_key": getattr(event, "rule_key", None),
                "severity": getattr(event, "severity", None),
                "message": getattr(event, "message", None),
                "observed_value": _json_safe_number(getattr(event, "observed_value", None)),
                "threshold_value": _json_safe_number(getattr(event, "threshold_value", None)),
                "scope": getattr(event, "scope", "portfolio"),
                "scope_key": getattr(event, "scope_key", None),
            }
        )
    return output


def _serialize_governance_report(report: Any) -> dict:
    governance_state = getattr(report, "governance_state", None)
    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    return {
        "decision": getattr(report, "decision", None),
        "reason": getattr(report, "reason", None),
        "compliance_state": getattr(governance_state, "status", None) if governance_state else None,
        "current_var": _json_safe_number(getattr(report, "current_var", None)),
        "new_var": _json_safe_number(getattr(report, "new_var", None)),
        "delta_var": _json_safe_number(getattr(report, "delta_var", None)),
        "current_es": _json_safe_number(getattr(report, "current_es", None)),
        "new_es": _json_safe_number(getattr(report, "new_es", None)),
        "delta_es": _json_safe_number(getattr(report, "delta_es", None)),
        "current_margin_used": _json_safe_number(getattr(report, "current_margin_used", None)),
        "new_margin_used": _json_safe_number(getattr(report, "new_margin_used", None)),
        "warnings": _serialize_limit_events(getattr(report, "warnings", None)),
        "breaches": _serialize_limit_events(getattr(report, "breaches", None)),
    }


def _serialize_recommendation_batch(batch: Any) -> dict:
    if batch is None:
        return {"items": []}

    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    def _serialize_recommendation_item(item: Any) -> Optional[dict]:
        action = getattr(item, "action", None)
        score = getattr(item, "recommendation_score", None)
        if action is None or score is None:
            return None
        raw_action_type = str(getattr(action, "action_type", "") or "")
        display_action = raw_action_type
        if (
            raw_action_type == "rebalance"
            and _json_safe_number(getattr(score, "margin_used_delta", None)) is not None
        ):
            margin_delta = float(getattr(score, "margin_used_delta", 0.0) or 0.0)
            if margin_delta < 0:
                display_action = "cut_margin"
        governance_report = getattr(item, "governance_report", None)
        return {
            "action_type": raw_action_type,
            "display_action": display_action,
            "symbol": getattr(action, "symbol", None),
            "delta_lots": _json_safe_number(getattr(action, "delta_lots", None)),
            "current_lots": _json_safe_number(getattr(action, "current_lots", None)),
            "projected_lots": _json_safe_number(getattr(action, "projected_lots", None)),
            "rationale": getattr(action, "rationale", None),
            "usefulness_score": _json_safe_number(getattr(score, "usefulness_score", None)),
            "score_delta": _json_safe_number(getattr(score, "score_delta", None)),
            "var_delta": _json_safe_number(getattr(score, "var_delta", None)),
            "es_delta": _json_safe_number(getattr(score, "es_delta", None)),
            "worst_scenario_loss_delta": _json_safe_number(
                getattr(score, "worst_scenario_loss_delta", None)
            ),
            "margin_used_delta": _json_safe_number(
                getattr(score, "margin_used_delta", None)
            ),
            "governance_feasible": bool(getattr(item, "governance_feasible", False)),
            "governance_decision": getattr(governance_report, "decision", None),
            "explanation": getattr(item, "explanation", None),
        }

    items = []
    for item in list(getattr(batch, "recommendations", []) or []):
        serialized = _serialize_recommendation_item(item)
        if serialized is not None:
            items.append(serialized)

    summary = dict(getattr(batch, "summary", {}) or {})
    capital_efficiency_items = []
    for item in list(summary.get("capital_efficiency", []) or []):
        capital_efficiency_items.append(
            {
                "symbol": item.get("symbol"),
                "gross_notional": _json_safe_number(item.get("gross_notional")),
                "portfolio_weight": _json_safe_number(item.get("portfolio_weight")),
                "risk_contribution_frac": _json_safe_number(item.get("risk_contribution_frac")),
                "capital_efficiency_ratio": _json_safe_number(item.get("capital_efficiency_ratio")),
            }
        )

    def _serialize_stage_list(values: Any) -> list[dict]:
        output = []
        for value in list(values or []):
            serialized = _serialize_recommendation_item(value)
            if serialized is not None:
                output.append(serialized)
        return output

    return {
        "items": items,
        "recommendation_count": int(
            summary.get("recommendation_count", len(items)) or len(items)
        ),
        "feasible_count": int(summary.get("feasible_count", 0) or 0),
        "top_action_type": summary.get("top_action_type"),
        "top_action_symbol": summary.get("top_action_symbol"),
        "top_usefulness_score": _json_safe_number(
            summary.get("top_usefulness_score")
        ),
        "marginal_risk_recommendation": _serialize_recommendation_item(
            summary.get("marginal_risk_recommendation")
        ),
        "allocation_candidates": _serialize_stage_list(summary.get("allocation_candidates")),
        "hedge_candidates": _serialize_stage_list(summary.get("hedge_candidates")),
        "rebalance_candidates": _serialize_stage_list(summary.get("rebalance_candidates")),
        "capital_efficiency": capital_efficiency_items,
    }


def _apply_leverage_override_to_state(
    state: PortfolioState,
    leverage_override: int,
) -> PortfolioState:
    effective_leverage = max(1, int(leverage_override))
    current_leverage = float(
        state.account.metadata.get("leverage")
        or state.metadata.get("account_leverage")
        or 0.0
    )
    current_margin_used = float(state.account.margin_used or 0.0)
    if current_leverage > 0.0:
        projected_margin_used = current_margin_used * (current_leverage / effective_leverage)
    else:
        projected_margin_used = current_margin_used
    new_account_metadata = {
        **dict(state.account.metadata or {}),
        "leverage": effective_leverage,
    }
    new_account = replace(
        state.account,
        margin_used=float(projected_margin_used),
        free_margin=float(state.account.equity) - float(projected_margin_used),
        metadata=new_account_metadata,
    )
    new_metadata = {
        **dict(state.metadata or {}),
        "account_leverage": effective_leverage,
    }
    return replace(
        state,
        account=new_account,
        metadata=new_metadata,
    )


def _estimate_state_margin_used(state: PortfolioState) -> float:
    positions = {
        str(symbol): float(lots)
        for symbol, lots in state.position_map.items()
        if abs(float(lots or 0.0)) > 1e-12
    }
    if not positions:
        return 0.0
    # Uses the migrated risk engine from backend.services.risk_engine.
    from backend.services.simulation.session_runtime import _SimulatorPortfolioStateRiskAdapter
    risk_engine = PortfolioRiskEngine(
        mt5_client=_SimulatorPortfolioStateRiskAdapter(state),
        timeframe=str(state.metadata.get("timeframe", "H1")),
        start_pos=0,
        end_pos=max(
            max((market.row_count for market in state.markets.values()), default=0),
            1,
        ),
    )
    estimated_margin = risk_engine.estimate_margin_used(positions)
    if estimated_margin is None:
        return float(state.account.margin_used or 0.0)
    return float(estimated_margin)


def _serialize_what_if_comparison(comparison: Any) -> dict:
    if comparison is None:
        return {}

    def _json_safe_number(value: Any) -> Any:
        if isinstance(value, (int, float)):
            numeric = float(value)
            if not math.isfinite(numeric):
                return None
            return numeric
        return value

    summary = dict(getattr(comparison, "summary", {}) or {})
    projected_snapshot = getattr(comparison, "projected_snapshot", None)
    projected_scorecard = getattr(comparison, "projected_scorecard", None)
    projected_recommendations = getattr(comparison, "projected_recommendations", None)
    baseline_frame = getattr(comparison, "baseline_frame", None)

    def _stress_map(snapshot: Any) -> Dict[str, Dict[str, Any]]:
        if snapshot is None:
            return {}
        rows = list(getattr(snapshot, "metric_rows", []) or [])
        scenario_map: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if getattr(row, "family", None) != "stress_risk":
                continue
            scope_key = getattr(row, "scope_key", None)
            metric_key = getattr(row, "metric_key", None)
            if getattr(row, "scope", None) == "scenario" and scope_key:
                bucket = scenario_map.setdefault(
                    str(scope_key),
                    {
                        "scenario": str(scope_key),
                        "context": dict(getattr(row, "context", {}) or {}),
                    },
                )
                if metric_key == "scenario_loss":
                    bucket["loss"] = _json_safe_number(getattr(row, "numeric_value", None))
                elif metric_key == "stressed_var":
                    bucket["stressed_var"] = _json_safe_number(getattr(row, "numeric_value", None))
                elif metric_key == "stressed_es":
                    bucket["stressed_es"] = _json_safe_number(getattr(row, "numeric_value", None))
        return scenario_map

    baseline_stress = _stress_map(baseline_frame.snapshot if baseline_frame is not None else None)
    projected_stress = _stress_map(projected_snapshot)
    stress_scenarios = []
    for scenario_name in sorted(set(baseline_stress.keys()) | set(projected_stress.keys())):
        baseline_item = baseline_stress.get(scenario_name, {})
        projected_item = projected_stress.get(scenario_name, {})
        baseline_loss = baseline_item.get("loss")
        projected_loss = projected_item.get("loss")
        stress_scenarios.append(
            {
                "scenario": scenario_name,
                "baseline_loss": baseline_loss,
                "projected_loss": projected_loss,
                "loss_delta": (
                    _json_safe_number(float(projected_loss) - float(baseline_loss))
                    if isinstance(baseline_loss, (int, float)) and isinstance(projected_loss, (int, float))
                    else None
                ),
                "baseline_stressed_var": baseline_item.get("stressed_var"),
                "projected_stressed_var": projected_item.get("stressed_var"),
                "baseline_stressed_es": baseline_item.get("stressed_es"),
                "projected_stressed_es": projected_item.get("stressed_es"),
                "context": projected_item.get("context") or baseline_item.get("context") or {},
            }
        )

    return {
        "summary": {key: _json_safe_number(value) for key, value in summary.items()},
        "actions": [
            {
                "action_type": getattr(action, "action_type", None),
                "symbol": getattr(action, "symbol", None),
                "delta_lots": _json_safe_number(getattr(action, "delta_lots", None)),
                "target_lots": _json_safe_number(getattr(action, "target_lots", None)),
                "rationale": getattr(action, "rationale", None),
            }
            for action in list(getattr(comparison, "actions", []) or [])
        ],
        "baseline": {
            "compliance_state": baseline_frame.snapshot.summary.get("compliance_state")
            if baseline_frame is not None
            else None,
            "overall_risk_quality_score": _json_safe_number(
                baseline_frame.scorecard.summary.get("overall_risk_quality_score")
                if baseline_frame is not None
                else None
            ),
        },
        "projected": {
            "compliance_state": projected_snapshot.summary.get("compliance_state")
            if projected_snapshot is not None
            else None,
            "governance_decision": projected_snapshot.summary.get("governance_decision")
            if projected_snapshot is not None
            else None,
            "governance_reason": projected_snapshot.summary.get("governance_reason")
            if projected_snapshot is not None
            else None,
            "overall_risk_quality_score": _json_safe_number(
                projected_scorecard.summary.get("overall_risk_quality_score")
                if projected_scorecard is not None
                else None
            ),
            "risk_snapshot": {
                "portfolio_var": _json_safe_number(
                    projected_snapshot.summary.get("portfolio_var")
                    if projected_snapshot is not None
                    else None
                ),
                "portfolio_es": _json_safe_number(
                    projected_snapshot.summary.get("portfolio_es")
                    if projected_snapshot is not None
                    else None
                ),
                "margin_used": _json_safe_number(
                    projected_snapshot.summary.get("margin_used")
                    if projected_snapshot is not None
                    else None
                ),
                "compliance_state": projected_snapshot.summary.get("compliance_state")
                if projected_snapshot is not None
                else None,
            },
        },
        "projected_recommendations": _serialize_recommendation_batch(
            projected_recommendations
        ),
        "stress_scenarios": stress_scenarios,
        "stress_summary": {
            "baseline_worst_scenario_name": baseline_frame.snapshot.summary.get("worst_scenario_name")
            if baseline_frame is not None
            else None,
            "baseline_worst_scenario_loss": _json_safe_number(
                baseline_frame.snapshot.summary.get("worst_scenario_loss")
                if baseline_frame is not None
                else None
            ),
            "projected_worst_scenario_name": projected_snapshot.summary.get("worst_scenario_name")
            if projected_snapshot is not None
            else None,
            "projected_worst_scenario_loss": _json_safe_number(
                projected_snapshot.summary.get("worst_scenario_loss")
                if projected_snapshot is not None
                else None
            ),
        },
    }
