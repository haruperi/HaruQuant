"""ADK-style runner entities for HaruQuant."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from haruquant.utils import logger
from .llm_runtime import LLMRuntime


@dataclass(frozen=True)
class ADKRunRequest:
    workflow_id: str
    correlation_id: str
    agent_name: str
    input_payload: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None
    allowed_tools: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ADKRunResult:
    workflow_id: str
    correlation_id: str
    agent_name: str
    model: str
    final_state: str
    output_payload: Dict[str, Any]
    latency_ms: int
    token_usage: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ADKRunnerConfig:
    runner_name: str
    default_model: Optional[str] = None


class ADKRunnerService:
    """Service to run agents with ADK-style requests and results."""

    def __init__(self, config: ADKRunnerConfig) -> None:
        self.config = config

    def run(self, agent: LLMRuntime, request: ADKRunRequest) -> ADKRunResult:
        start_time = time.perf_counter()
        
        # Extract system prompt and task from input_payload
        system_prompt = request.input_payload.get("_system_prompt", "You are a helpful assistant.")
        user_message = request.input_payload.get("task", request.input_payload.get("question", str(request.input_payload)))
        
        # Call the LLM
        response = agent.call(system_prompt=system_prompt, user_message=user_message)
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        return ADKRunResult(
            workflow_id=request.workflow_id,
            correlation_id=request.correlation_id,
            agent_name=request.agent_name,
            model=agent.model,
            final_state="completed",
            output_payload=response,
            latency_ms=latency_ms,
            token_usage={
                "input_tokens": response.get("input_tokens", 0),
                "output_tokens": response.get("output_tokens", 0),
                "total_tokens": response.get("total_tokens", 0),
            },
        )
