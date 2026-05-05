"""Normalization and validation for StrategyBlueprint contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from contracts.strategy_blueprint.model import StrategyBlueprint

from .blueprint_defaults import DEFAULT_TIMEFRAME, default_assets, infer_strategy_type, slugify, title_case_idea


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _deep_get(candidate: dict[str, Any], *keys: str) -> Any:
    current: Any = candidate
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


@dataclass(frozen=True)
class BlueprintValidationResult:
    blueprint: StrategyBlueprint
    issues: tuple[str, ...]
    ready: bool


class StrategyBlueprintValidator:
    """Apply deterministic defaults and validate the resulting blueprint."""

    def normalize_candidate(
        self,
        candidate: dict[str, Any],
        *,
        source_idea: str | None = None,
    ) -> dict[str, Any]:
        payload_candidate = dict(candidate.get("payload", {}))
        source_text = source_idea or payload_candidate.get("source_idea") or candidate.get("source_idea") or "Unnamed strategy idea"
        strategy_type = infer_strategy_type(payload_candidate, source_text)

        asset_scope = dict(payload_candidate.get("asset_scope", {}))
        assets = asset_scope.get("assets") or payload_candidate.get("assets") or default_assets(strategy_type)
        timeframe = asset_scope.get("timeframe") or payload_candidate.get("timeframe") or DEFAULT_TIMEFRAME
        data_granularity = asset_scope.get("data_granularity") or timeframe

        ignore_sl_tp = bool(_deep_get(payload_candidate, "risk_management", "ignore_stop_loss_take_profit"))
        stop_loss = _deep_get(payload_candidate, "risk_management", "stop_loss")
        take_profit = _deep_get(payload_candidate, "risk_management", "take_profit")
        additional_rules = list(_deep_get(payload_candidate, "risk_management", "additional_rules") or [])

        assumptions_applied = list(payload_candidate.get("assumptions_applied", []))
        defaults_used = list(payload_candidate.get("assumption_defaults_used", []))

        if not payload_candidate.get("strategy_name"):
            assumptions_applied.append("Strategy name derived from rough human idea.")
            defaults_used.append("strategy_name=derived_from_idea")
        if not payload_candidate.get("strategy_id"):
            defaults_used.append("strategy_id=slugified_strategy_name")
        if not asset_scope.get("assets") and not payload_candidate.get("assets"):
            assumptions_applied.append(f"Assets defaulted for {strategy_type} strategy.")
            defaults_used.append(f"assets={','.join(default_assets(strategy_type)[:3])}")
        if not asset_scope.get("timeframe") and not payload_candidate.get("timeframe"):
            assumptions_applied.append("Timeframe defaulted to Daily (1D).")
            defaults_used.append("timeframe=1D")
        if strategy_type == "technical" and "rsi" in source_text.lower() and not re.search(
            r"\brsi\s*\(?\s*\d{1,3}\s*\)?",
            source_text,
            flags=re.IGNORECASE,
        ):
            assumptions_applied.append("RSI parameter defaulted to 14 periods.")
            defaults_used.append("indicator_default=rsi_14")
        if not ignore_sl_tp:
            if not stop_loss:
                stop_loss = (
                    "7% portfolio-level drawdown stop or per-asset 7% stop-loss."
                    if strategy_type in {"portfolio", "allocation", "rotation"}
                    else "7% below entry price"
                )
                defaults_used.append("risk_default=7pct_stop_loss")
            if not take_profit:
                take_profit = (
                    "10% per-asset take-profit or rebalance-driven profit capture."
                    if strategy_type in {"portfolio", "allocation", "rotation"}
                    else "10% above entry price"
                )
                defaults_used.append("risk_default=10pct_take_profit")
        position_sizing_candidate = payload_candidate.get("position_sizing")
        if not isinstance(position_sizing_candidate, dict) or not position_sizing_candidate.get("sizing_rule"):
            if strategy_type in {"portfolio", "allocation", "rotation"}:
                assumptions_applied.append("Portfolio position sizing defaulted to equal weight.")
                defaults_used.append("position_sizing=equal_weight")
            else:
                assumptions_applied.append("Single-asset sizing defaulted to full capital.")
                defaults_used.append("position_sizing=full_capital")

        model_spec = payload_candidate.get("model_spec")
        if strategy_type == "ml" and not model_spec:
            model_spec = {
                "model_type": "DecisionTreeClassifier",
                "target_definition": "Predict whether next-day return is positive or negative.",
                "feature_set": ["return_1d", "volume", "rsi_14", "sma_20_gap"],
                "prediction_horizon": "1D ahead",
            }
            assumptions_applied.append("ML model spec defaulted from rulebook.")
            defaults_used.append("ml_model=decision_tree_classifier")

        portfolio_construction = payload_candidate.get("portfolio_construction")
        if strategy_type in {"portfolio", "allocation", "rotation"} and not portfolio_construction:
            method = "HRP" if "hrp" in source_text.lower() else "EqualWeight"
            portfolio_construction = {
                "method": method,
                "rebalance_frequency": "Weekly",
                "objective": "Risk-balanced diversified allocation",
            }
            assumptions_applied.append("Portfolio construction defaults applied.")
            defaults_used.append(f"portfolio_method={method.lower()}")

        entry_logic = payload_candidate.get("entry_logic") or candidate.get("entry_logic") or ["Define a precise entry rule from the supplied idea."]
        exit_logic = payload_candidate.get("exit_logic") or candidate.get("exit_logic") or ["Exit when the entry thesis is invalidated or the risk rule triggers."]

        normalized = {
            "schema_version": candidate.get("schema_version", "1.0.0"),
            "contract_type": "StrategyBlueprint",
            "workflow_id": candidate.get("workflow_id", "wf_strategy_creation"),
            "correlation_id": candidate.get("correlation_id", "corr_strategy_creation"),
            "causation_id": candidate.get("causation_id", "evt_strategy_creation"),
            "timestamp_utc": candidate.get("timestamp_utc", _now_iso()),
            "originator": candidate.get("originator", {"type": "agent", "id": "strategy_creator_agent"}),
            "environment": candidate.get("environment", "paper"),
            "operating_mode": candidate.get("operating_mode", "MODE-001"),
            "payload": {
                "strategy_id": payload_candidate.get("strategy_id") or slugify(payload_candidate.get("strategy_name") or title_case_idea(source_text)),
                "strategy_name": payload_candidate.get("strategy_name") or title_case_idea(source_text),
                "source_idea": source_text,
                "strategy_type": strategy_type,
                "asset_scope": {
                    "assets": assets,
                    "timeframe": timeframe,
                    "data_granularity": data_granularity,
                    "asset_notes": asset_scope.get("asset_notes") or ("Portfolio default universe applied." if strategy_type in {"portfolio", "allocation", "rotation"} else "Single-asset default applied."),
                },
                "entry_logic": entry_logic if isinstance(entry_logic, list) else [str(entry_logic)],
                "exit_logic": exit_logic if isinstance(exit_logic, list) else [str(exit_logic)],
                "risk_management": {
                    "stop_loss": None if ignore_sl_tp else stop_loss,
                    "take_profit": None if ignore_sl_tp else take_profit,
                    "ignore_stop_loss_take_profit": ignore_sl_tp,
                    "additional_rules": additional_rules,
                },
                "position_sizing": {
                    "sizing_rule": _deep_get(payload_candidate, "position_sizing", "sizing_rule")
                    or ("Allocate capital equally across selected assets." if strategy_type in {"portfolio", "allocation", "rotation"} else "Use full capital per trade."),
                    "leverage": float(_deep_get(payload_candidate, "position_sizing", "leverage") or 1.0),
                    "allocation_notes": _deep_get(payload_candidate, "position_sizing", "allocation_notes")
                    or ("Portfolio equal-weight default applied." if strategy_type in {"portfolio", "allocation", "rotation"} else "Single-asset default applied."),
                },
                "model_spec": model_spec,
                "portfolio_construction": portfolio_construction,
                "assumptions_applied": assumptions_applied,
                "assumption_defaults_used": defaults_used,
                "backtest_readiness": payload_candidate.get("backtest_readiness", "ready"),
                "render_target": "template_strategy",
            },
        }
        return normalized

    def validate(
        self,
        candidate: dict[str, Any],
        *,
        source_idea: str | None = None,
    ) -> BlueprintValidationResult:
        normalized = self.normalize_candidate(candidate, source_idea=source_idea)
        blueprint = StrategyBlueprint.model_validate(normalized)

        issues: list[str] = []
        payload = blueprint.payload
        if payload.strategy_type == "portfolio" and len(payload.asset_scope.assets) < 2:
            issues.append("Portfolio strategies require at least two assets.")
        if payload.strategy_type == "ml" and payload.model_spec is None:
            issues.append("ML strategies require a model specification.")
        if payload.strategy_type in {"portfolio", "allocation", "rotation"} and payload.portfolio_construction is None:
            issues.append("Portfolio-style strategies require portfolio construction settings.")
        if not payload.risk_management.ignore_stop_loss_take_profit:
            if not payload.risk_management.stop_loss:
                issues.append("Stop-loss must be defined unless explicitly ignored.")
            if not payload.risk_management.take_profit:
                issues.append("Take-profit must be defined unless explicitly ignored.")

        readiness = payload.backtest_readiness == "ready" and not issues
        if not readiness:
            blueprint = blueprint.model_copy(
                update={
                    "payload": blueprint.payload.model_copy(update={"backtest_readiness": "needs_review"})
                }
            )
        return BlueprintValidationResult(blueprint=blueprint, issues=tuple(issues), ready=readiness)
