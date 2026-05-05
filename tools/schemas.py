"""Shared schemas for agent tool contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["read_only", "write", "critical"]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    category: str
    risk_level: RiskLevel
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_agents: list[str]
    requires_audit: bool = True
    requires_risk_governor: bool = False
    requires_human_approval: bool = False
    enabled: bool = True


class ToolStubRequest(BaseModel):
    """Generic contract for tools that are registered before implementation."""

    model_config = ConfigDict(extra="allow")

    reason: str | None = Field(
        default=None,
        description="Why the agent wants to call this tool.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific input payload.",
    )


class ToolStubResult(BaseModel):
    tool_name: str
    status: Literal["stub", "success", "failed", "blocked"] = "stub"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    audit_required: bool = True


class PolicyValidationRequest(BaseModel):
    policy_name: str
    content: str
    context: dict[str, Any] = Field(default_factory=dict)


class PermissionValidationRequest(BaseModel):
    agent_name: str
    tool_name: str
    context: dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    task_id: str | None = None
    parent_task_id: str | None = None
    assigned_agent: str | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataRequest(BaseModel):
    symbol: str | None = None
    timeframe: str | None = None
    start: str | None = None
    end: str | None = None
    count: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyRequest(BaseModel):
    strategy_id: str | None = None
    version: str | None = None
    spec: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeRequest(BaseModel):
    strategy_id: str | None = None
    version: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulationRequest(BaseModel):
    simulation_id: str | None = None
    strategy_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    start: str | None = None
    end: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class BacktestResultSummary(BaseModel):
    run_id: str
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class AnalyticsRequest(BaseModel):
    run_id: str | None = None
    trades: list[dict[str, Any]] = Field(default_factory=list)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskRequest(BaseModel):
    account_id: str | None = None
    symbol: str | None = None
    order: dict[str, Any] = Field(default_factory=dict)
    portfolio: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    volume: float
    order_type: str
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_approval_token: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    status: str
    order_id: str | None = None
    receipt_id: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    report_id: str | None = None
    report_type: str | None = None
    format: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRequest(BaseModel):
    subject_id: str | None = None
    event_type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
