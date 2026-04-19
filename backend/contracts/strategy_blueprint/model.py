"""StrategyBlueprint canonical contract models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


StrategyType = Literal[
    "technical",
    "portfolio",
    "ml",
    "factor",
    "stat_arb",
    "allocation",
    "rotation",
]

ReadinessState = Literal["ready", "needs_review"]
RenderTarget = Literal["template_strategy"]


class AssetScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[str] = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    data_granularity: str = Field(min_length=1)
    asset_notes: str | None = None


class RiskManagement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stop_loss: str | None = None
    take_profit: str | None = None
    ignore_stop_loss_take_profit: bool = False
    additional_rules: list[str] = Field(default_factory=list)


class PositionSizing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sizing_rule: str = Field(min_length=1)
    leverage: float = Field(ge=0.0, default=1.0)
    allocation_notes: str | None = None


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_type: str = Field(min_length=1)
    target_definition: str = Field(min_length=1)
    feature_set: list[str] = Field(default_factory=list)
    prediction_horizon: str = Field(min_length=1)


class PortfolioConstruction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1)
    rebalance_frequency: str = Field(min_length=1)
    objective: str = Field(min_length=1)


class StrategyBlueprintPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    source_idea: str = Field(min_length=1)
    strategy_type: StrategyType
    asset_scope: AssetScope
    entry_logic: list[str] = Field(min_length=1)
    exit_logic: list[str] = Field(min_length=1)
    risk_management: RiskManagement
    position_sizing: PositionSizing
    model_spec: ModelSpec | None = None
    portfolio_construction: PortfolioConstruction | None = None
    assumptions_applied: list[str] = Field(default_factory=list)
    assumption_defaults_used: list[str] = Field(default_factory=list)
    backtest_readiness: ReadinessState = "ready"
    render_target: RenderTarget = "template_strategy"


class StrategyBlueprint(CanonicalEnvelope):
    """Canonical envelope specialization for StrategyBlueprint."""

    contract_type: Literal["StrategyBlueprint"] = "StrategyBlueprint"
    payload: StrategyBlueprintPayload


__all__ = [
    "AssetScope",
    "ModelSpec",
    "Originator",
    "PortfolioConstruction",
    "PositionSizing",
    "ReadinessState",
    "RenderTarget",
    "RiskManagement",
    "StrategyBlueprint",
    "StrategyBlueprintPayload",
    "StrategyType",
]
