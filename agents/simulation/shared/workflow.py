"""Department workflow for Simulation agents."""

from __future__ import annotations

import asyncio
from typing import Any

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentResponse

from ..backtest_agent.service import BacktestAgentService
from ..backtest_analyst_agent.service import BacktestAnalystAgentService
from ..optimization_agent.service import OptimizationAgentService
from ..optimization_comparator_agent.service import OptimizationComparatorAgentService
from ..robustness_agent.service import RobustnessAgentService
from ..simulation_evidence_curator_agent.service import SimulationEvidenceCuratorAgentService
from ..simulation_orchestrator_agent.service import SimulationOrchestratorAgentService
from ..statistical_validation_agent.service import StatisticalValidationAgentService


async def run_simulation_department_workflow(payload: dict[str, Any]) -> dict[str, AgentResponse]:
    context = AgentContext(session_id=payload.get("session_id", "simulation-workflow"))
    services = [
        SimulationOrchestratorAgentService(),
        BacktestAgentService(),
        BacktestAnalystAgentService(),
        OptimizationAgentService(),
        OptimizationComparatorAgentService(),
        RobustnessAgentService(),
        StatisticalValidationAgentService(),
        SimulationEvidenceCuratorAgentService(),
    ]
    responses: dict[str, AgentResponse] = {}
    for service in services:
        request = AgentRequest(request_id=f"sim-{service.agent_name}", agent_name=service.agent_name, task=payload.get("task", "Run simulation department workflow"), payload=payload)
        responses[service.agent_name] = await service.run(request, context)
    return responses


def run_simulation_department_workflow_sync(payload: dict[str, Any]) -> dict[str, AgentResponse]:
    return asyncio.run(run_simulation_department_workflow(payload))
