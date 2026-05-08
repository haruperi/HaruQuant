"""StrategyBlueprint contract used by strategy design services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts import Originator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssetScope(_Model):
    assets: list[str] = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    data_granularity: str = Field(min_length=1)
    asset_notes: str | None = None


class RiskManagement(_Model):
    stop_loss: str | None = None
    take_profit: str | None = None
    ignore_stop_loss_take_profit: bool = False
    additional_rules: list[str] = Field(default_factory=list)


class PositionSizing(_Model):
    sizing_rule: str = Field(min_length=1)
    leverage: float = 1.0
    allocation_notes: str | None = None


class ModelSpec(_Model):
    model_type: str = Field(min_length=1)
    target_definition: str | None = None
    feature_set: list[str] = Field(default_factory=list)
    prediction_horizon: str | None = None


class PortfolioConstruction(_Model):
    method: str = Field(min_length=1)
    rebalance_frequency: str | None = None
    objective: str | None = None


class StrategyBlueprintPayload(_Model):
    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    source_idea: str = Field(min_length=1)
    strategy_type: str = Field(min_length=1)
    asset_scope: AssetScope
    entry_logic: list[str] = Field(min_length=1)
    exit_logic: list[str] = Field(min_length=1)
    risk_management: RiskManagement
    position_sizing: PositionSizing
    model_spec: ModelSpec | None = None
    portfolio_construction: PortfolioConstruction | None = None
    assumptions_applied: list[str] = Field(default_factory=list)
    assumption_defaults_used: list[str] = Field(default_factory=list)
    backtest_readiness: Literal["ready", "needs_review"] = "ready"
    render_target: str = "template_strategy"


class StrategyBlueprint(_Model):
    schema_version: str = "1.0.0"
    contract_type: Literal["StrategyBlueprint"] = "StrategyBlueprint"
    workflow_id: str
    correlation_id: str
    causation_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    originator: Originator
    environment: str = "paper"
    operating_mode: str = "MODE-001"
    payload: StrategyBlueprintPayload


__all__ = [
    "AssetScope",
    "ModelSpec",
    "PortfolioConstruction",
    "PositionSizing",
    "RiskManagement",
    "StrategyBlueprint",
    "StrategyBlueprintPayload",
]
