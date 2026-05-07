"""Strategy Creation Department workflow helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentResponse


AGENT_ORDER = (
    "strategy_creator_agent",
    "strategy_rule_normalizer_agent",
    "strategy_template_selector_agent",
    "strategy_risk_assumption_agent",
    "strategy_cost_execution_agent",
    "strategy_test_plan_agent",
    "strategy_spec_validator_agent",
    "strategy_codegen_agent",
    "strategy_reviewer_agent",
    "strategy_spec_storage_agent",
    "strategy_code_storage_agent",
    "strategy_handoff_agent",
)


@dataclass
class StrategyCreationWorkflowPackage:
    strategy_creation_plan: list[str]
    agent_responses: dict[str, AgentResponse]
    final_strategy_creation_package: dict[str, Any]
    validation_backtesting_handoff: dict[str, Any]
    audit: dict[str, Any]


def _service_for(agent_name: str):
    module_name = f"agents.strategy_development.{agent_name}.service"
    class_name = "".join(part.title() for part in agent_name.split("_")) + "Service"
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)()


async def run_strategy_creation_workflow(request: AgentRequest, context: AgentContext) -> StrategyCreationWorkflowPackage:
    responses: dict[str, AgentResponse] = {}
    for agent_name in AGENT_ORDER:
        responses[agent_name] = await _service_for(agent_name).run(request.model_copy(update={"agent_name": agent_name}, deep=True), context)
    final = {
        "strategy_spec": responses["strategy_creator_agent"].artifacts["strategy_spec"],
        "strategy_code_package": responses["strategy_codegen_agent"].artifacts["strategy_code_package"],
        "strategy_review_report": responses["strategy_reviewer_agent"].artifacts["strategy_review_report"],
        "handoff": responses["strategy_handoff_agent"].artifacts["strategy_validation_handoff_package"],
    }
    return StrategyCreationWorkflowPackage(
        strategy_creation_plan=list(AGENT_ORDER),
        agent_responses=responses,
        final_strategy_creation_package=final,
        validation_backtesting_handoff=final["handoff"],
        audit={"responses_validated": len(responses), "ceo_gateway_surface_ready": True},
    )


def run_strategy_creation_workflow_sync(request: AgentRequest, context: AgentContext) -> StrategyCreationWorkflowPackage:
    return asyncio.run(run_strategy_creation_workflow(request, context))
