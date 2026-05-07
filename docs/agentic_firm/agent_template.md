# HaruQuant Agent Template

**Purpose:** Standardize how every HaruQuant agent is built, tested, logged, evaluated, and later connected into the full agentic trading firm.

**Core principle:** Each agent is a deterministic service with optional LLM reasoning inside it. The LLM may assist with analysis, summarization, classification, explanation, ranking, or proposal generation, but the final response or decision must be controlled by deterministic code.

---

## 1. Core Rule for Every HaruQuant Agent

Every agent must follow this execution pattern:

```text
Validate Input
-> Gather Evidence / Context
-> Optional LLM Reasoning
-> Deterministic Policy Decision
-> Structured Output
-> Audit Log
-> Evaluation Test
```

The LLM is allowed to help with:

- Analysis
- Summarization
- Classification
- Explanation
- Ranking
- Idea generation
- Signal interpretation
- Report drafting

The LLM is not allowed to make the final uncontrolled decision.

Final decisions must always come from deterministic code:

```text
LLM output = proposal
Deterministic policy = final decision
```

This is the main safety and reliability rule for HaruQuant agents.

---

## 2. Why This Template Exists

HaruQuant will contain many specialist agents that can work independently and later collaborate through the existing CEO Agent, Planner Agent, and CEO chat runtime.

Because different coding agents or developers may implement different specialists, every agent must follow the same structure.

The goal is to guarantee:

- Consistent file structure
- Consistent service interface
- Consistent input/output contracts
- Consistent logging
- Consistent audit behavior
- Consistent deterministic decision layer
- Consistent evaluation pattern
- Easy debugging
- Easy orchestration later

This prevents the full system from becoming a collection of unrelated prompts.

---

## 3. Architectural Position

Every specialist agent should be built as an isolated, testable module first.

Only after each agent works alone should it be connected to the broader multi-agent firm.

Recommended development flow:

```text
Build Specialist Agent Alone
-> Test Specialist Agent Alone
-> Validate Output Contract
-> Add Evaluation Tests
-> Add Logging and Audit
-> Connect to Department Workflow
-> Register with Planner
-> Connect through CEOChatGateway
-> Let CEO Agent synthesize the final user-facing memo
```

`services/ceo_gateway.py`, `agents/executive/planner_agent/service.py`, and `agents/executive/ceo_agent/service.py` already exist as the chat entrypoint and executive orchestration layer.

Build every specialist agent as a reliable standalone service first. Only after its contracts, tests, audit metadata, deterministic policy, and permission checks pass should it be registered with Planner and surfaced through CEOChatGateway.

The AI chat UI must not call specialist agents directly. Chat requests enter through `services/ceo_gateway.py`; Planner decides which specialist evidence is needed; CEOAgent owns the final user-facing synthesis.

---

## 4. Standard Folder Structure

Use this structure for every individual agent:

```text
agents/
  _shared/
    __init__.py
    base_contracts.py
    base_agent.py
    logging.py
    tracing.py
    exceptions.py
    deterministic.py
    evaluation.py

  executive/
    ceo_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
    planner_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
  runtime/
    tool_executor.py

  research/
    market_intelligence_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

  strategy_development/
    strategy_creator_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/
        test_contracts.py
        test_deterministic_policy.py
        test_service.py
        test_agent_smoke.py

  validation_backtesting/
    backtest_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

  risk_portfolio/
    risk_reviewer_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

  execution/
    execution_planner_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

  operations_audit/
    audit_compliance_agent/
      __init__.py
      agent.py
      contracts.py
      prompts.py
      deterministic_policy.py
      tools.py
      service.py
      evaluator.py
      README.md
      tests/

services/
  ceo_gateway.py

tools/
  read_only/

policies/
  tool_policy.py
```

Each agent folder must contain the same file names. The content differs by agent, but the structure does not.

---

## 5. Required Files for Each Agent

Each agent must include:

```text
__init__.py
agent.py
contracts.py
prompts.py
deterministic_policy.py
tools.py
service.py
evaluator.py
README.md
tests/
```

### File Responsibilities

| File                        | Responsibility                                                            |
| --------------------------- | ------------------------------------------------------------------------- |
| `agent.py`                | Creates the optional LLM agent wrapper or runtime adapter boundary.        |
| `contracts.py`            | Defines agent-specific input/output schemas.                              |
| `prompts.py`              | Stores versioned prompts and role instructions.                           |
| `deterministic_policy.py` | Converts evidence and LLM analysis into the final deterministic decision. |
| `tools.py`                | Contains the tools this agent is allowed to call.                         |
| `service.py`              | Stable public interface used by the rest of HaruQuant.                    |
| `evaluator.py`            | Agent-specific quality and safety checks.                                 |
| `README.md`               | Human-readable documentation for the agent.                               |
| `tests/`                  | Unit, policy, service, and smoke tests.                                   |

---

## 6. Shared Contracts

Create this shared contract file first.

```python
# agents/_shared/base_contracts.py

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    SUCCESS = "success"
    REJECTED = "rejected"
    NEEDS_MORE_CONTEXT = "needs_more_context"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceItem(BaseModel):
    source: str
    description: str
    value: Any | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class AgentRequest(BaseModel):
    request_id: str
    user_id: str = "haruperi"
    agent_name: str
    task: str
    payload: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class AgentContext(BaseModel):
    session_id: str | None = None
    portfolio_state: dict[str, Any] = Field(default_factory=dict)
    market_state: dict[str, Any] = Field(default_factory=dict)
    strategy_state: dict[str, Any] = Field(default_factory=dict)
    risk_state: dict[str, Any] = Field(default_factory=dict)


class LLMAnalysis(BaseModel):
    summary: str
    observations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    raw_model_output: str | None = None


class AgentDecision(BaseModel):
    status: AgentStatus
    decision: str
    confidence: ConfidenceLevel
    risk_level: RiskLevel
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    request_id: str
    agent_name: str
    status: AgentStatus
    evidence: list[EvidenceItem] = Field(default_factory=list)
    llm_analysis: LLMAnalysis | None = None
    decision: AgentDecision
    artifacts: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)
```

`AgentResponse.audit` must include enough provenance for `services/ceo_gateway.py` to surface the specialist output in chat metadata.

Recommended audit keys:

```text
context_revision
evidence_refs
tools_used
permission_profile
model_provider
model_name
fallback_used
policy_version
prompt_version
```

---

## 7. Shared Base Agent Interface

This optional base class forces every agent service to expose the same lifecycle.

```python
# agents/_shared/base_agent.py

from __future__ import annotations

from abc import ABC, abstractmethod

from .base_contracts import (
    AgentRequest,
    AgentContext,
    AgentResponse,
    EvidenceItem,
    LLMAnalysis,
    AgentDecision,
)


class HaruQuantAgentService(ABC):
    agent_name: str

    @abstractmethod
    async def run(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResponse:
        pass

    @abstractmethod
    def gather_evidence(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> list[EvidenceItem]:
        pass

    @abstractmethod
    async def run_llm_analysis(
        self,
        request: AgentRequest,
        context: AgentContext,
        evidence: list[EvidenceItem],
    ) -> LLMAnalysis | None:
        pass

    @abstractmethod
    def make_deterministic_decision(
        self,
        request: AgentRequest,
        context: AgentContext,
        evidence: list[EvidenceItem],
        llm_analysis: LLMAnalysis | None,
    ) -> AgentDecision:
        pass
```

---

## 8. Standard Agent-Specific Contracts

Each agent may extend the shared contracts with its own domain-specific request and response models.

```python
# agents/research/market_intelligence_agent/contracts.py

from __future__ import annotations

from pydantic import BaseModel, Field


class MarketIntelligencePayload(BaseModel):
    symbol: str = Field(..., examples=["EURUSD"])
    timeframe: str = Field(default="H1")
    include_news: bool = True
    include_session_context: bool = True
    include_volatility_context: bool = True


class MarketIntelligenceArtifact(BaseModel):
    symbol: str
    timeframe: str
    session: str | None = None
    spread_pips: float | None = None
    volatility_state: str | None = None
    news_risk: str | None = None
```

Rules:

- Do not use raw dictionaries everywhere if a schema would improve safety.
- Use Pydantic models for anything that crosses agent boundaries.
- Keep internal helper structures private unless another agent needs them.

---

## 9. Standard Prompt File

Every prompt must be versioned.

```python
# agents/research/market_intelligence_agent/prompts.py

AGENT_PROMPT_VERSION = "market_intelligence_agent_prompt_v1"

SYSTEM_INSTRUCTIONS = '''
You are the HaruQuant Market Intelligence Agent.

Your job:
- Analyze market context.
- Summarize important market conditions.
- Identify volatility, macro, session, and news risks.
- Produce observations only.

You must not:
- Place trades.
- Approve trades.
- Override the Risk Governor.
- Invent market data.
- Return unstructured final decisions.

Your output is only an analytical proposal.
The deterministic policy layer will make the final decision.
'''
```

Prompt rules:

- Prompts live only in `prompts.py`.
- Prompts must not contain hidden business logic.
- Business logic belongs in `deterministic_policy.py`.
- Prompts must clearly state what the agent is forbidden to do.
- Prompts must remind the LLM that the deterministic policy layer makes the final decision.

---

## 10. Standard Tool File

Each agent must declare its allowed tools.

```python
# agents/research/market_intelligence_agent/tools.py

from typing import Any


def get_market_snapshot(symbol: str) -> dict[str, Any]:
    """
    Deterministic market data retrieval tool.

    Replace this stub with your real data service:
    - OHLCV
    - spread
    - volatility
    - session
    - macro/news flags
    """
    return {
        "symbol": symbol,
        "spread_pips": 1.2,
        "volatility_state": "normal",
        "session": "london",
        "news_risk": "low",
    }


TOOLS = [
    get_market_snapshot,
]
```

Tool rules:

- Tools must be explicit.
- Do not allow general unrestricted tools inside specialist agents.
- Do not let agents call execution tools unless they are execution-specific.
- Do not let research, strategy, validation, or reporting agents place trades.
- Tool output should be normalized into `EvidenceItem`.
- Tool calls should be logged.
- Any tool exposed to AI Chat by default must be read-only and pass through `tools/read_only/`, `policies/tool_policy.py`, and `agents/runtime/tool_executor.py`.
- Write-safe, write-controlled, or critical tools require explicit workflow approval and must not be exposed as casual chat tools.
- Specialist agents may expose read-only summaries to CEOChatGateway, but mutation tools require a governed workflow, permission check, and audit record.

---

## 11. Deterministic Policy Layer

This is the most important file in each agent.

It converts evidence and optional LLM analysis into the final decision.

```python
# agents/research/market_intelligence_agent/deterministic_policy.py

from agents._shared.base_contracts import (
    AgentDecision,
    AgentStatus,
    ConfidenceLevel,
    RiskLevel,
    EvidenceItem,
    LLMAnalysis,
)


def make_final_decision(
    evidence: list[EvidenceItem],
    llm_analysis: LLMAnalysis | None,
) -> AgentDecision:
    """
    Final deterministic decision layer.

    The LLM may suggest, but this function decides.
    """

    news_risk = None
    spread_pips = None
    volatility_state = None

    for item in evidence:
        if item.source == "market_snapshot":
            value = item.value or {}
            news_risk = value.get("news_risk")
            spread_pips = value.get("spread_pips")
            volatility_state = value.get("volatility_state")

    blocked_actions: list[str] = []
    allowed_actions: list[str] = ["summarize_market_context"]

    risk_level = RiskLevel.LOW
    confidence = ConfidenceLevel.MEDIUM
    reasons: list[str] = []

    if news_risk == "high":
        risk_level = RiskLevel.HIGH
        blocked_actions.append("new_trade_signal_generation")
        reasons.append("High news risk detected.")

    if spread_pips is not None and spread_pips > 3.0:
        risk_level = RiskLevel.HIGH
        blocked_actions.append("trade_execution")
        reasons.append("Spread exceeds maximum acceptable threshold.")

    if volatility_state == "extreme":
        risk_level = RiskLevel.CRITICAL
        blocked_actions.append("trade_execution")
        blocked_actions.append("position_scaling")
        reasons.append("Extreme volatility state detected.")

    if not reasons:
        reasons.append("Market conditions are within normal monitoring limits.")
        confidence = ConfidenceLevel.HIGH

    return AgentDecision(
        status=AgentStatus.SUCCESS,
        decision="market_context_review_complete",
        confidence=confidence,
        risk_level=risk_level,
        allowed_actions=allowed_actions,
        blocked_actions=blocked_actions,
        reasons=reasons,
    )
```

Deterministic policy rules:

- Never let raw LLM text become the final decision.
- LLM output can influence a decision only through validated, schema-constrained fields.
- Risk thresholds must be explicit.
- Rejection rules must be explicit.
- Missing evidence must be handled.
- Edge cases must be tested.
- The policy must produce a valid `AgentDecision` every time.

---

## 12. Optional LLM Agent Factory

Each agent that uses an LLM should expose a `build_agent()` or equivalent runtime factory function.

Google ADK is allowed, but it is not the only approved runtime boundary. Agents may use Google ADK or the HaruQuant runtime/model adapter. Model provider selection must come from `HARUQUANT_AGENT_MODEL` or approved model-routing configuration, not from hardcoded agent-specific secrets.

```python
# agents/research/market_intelligence_agent/agent.py

from google.adk.agents import Agent

from .prompts import SYSTEM_INSTRUCTIONS
from .tools import TOOLS


def build_agent() -> Agent:
    return Agent(
        name="market_intelligence_agent",
        model="gemini-3.1-flash-lite-preview",
        instructions=SYSTEM_INSTRUCTIONS,
        tools=TOOLS,
    )
```

Notes:

- Keep LLM runtime construction isolated in `agent.py`.
- Do not place business logic in `agent.py`.
- If using Google ADK, use the exact constructor signature that matches the installed ADK version.
- If using the HaruQuant runtime/model adapter, route through the shared runtime layer and the approved model environment variables.
- Never read provider API keys directly inside specialist agent business logic.

---

## 13. Standard Service Interface

The service is the stable interface used by the rest of HaruQuant.

No other module should call the raw ADK agent directly.

No chat UI module should call a specialist service directly. Specialist services are connected to chat through Planner and `services/ceo_gateway.py`.

```python
# agents/research/market_intelligence_agent/service.py

from __future__ import annotations

import json
import logging
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents._shared.base_contracts import (
    AgentRequest,
    AgentContext,
    AgentResponse,
    EvidenceItem,
    LLMAnalysis,
)
from .agent import build_agent
from .deterministic_policy import make_final_decision
from .tools import get_market_snapshot

logger = logging.getLogger(__name__)


class MarketIntelligenceAgentService:
    agent_name = "market_intelligence_agent"
    app_name = "haruquant"

    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self.agent = build_agent()
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    async def run(
        self,
        request: AgentRequest,
        context: AgentContext,
    ) -> AgentResponse:
        logger.info(
            "Starting agent run",
            extra={
                "request_id": request.request_id,
                "agent_name": self.agent_name,
            },
        )

        evidence = self._gather_evidence(request)
        llm_analysis = await self._run_llm_analysis(request, context, evidence)
        decision = make_final_decision(evidence, llm_analysis)

        response = AgentResponse(
            request_id=request.request_id,
            agent_name=self.agent_name,
            status=decision.status,
            evidence=evidence,
            llm_analysis=llm_analysis,
            decision=decision,
            artifacts={},
            audit={
                "agent_name": self.agent_name,
                "policy_version": "deterministic_policy_v1",
                "prompt_version": "market_intelligence_agent_prompt_v1",
                "llm_used": llm_analysis is not None,
                "model_provider": "configured_runtime",
                "model_name": "from_HARUQUANT_AGENT_MODEL",
                "fallback_used": llm_analysis is None,
                "tools_used": ["get_market_snapshot"],
                "permission_profile": "research_read_only_v1",
                "evidence_refs": [item.source for item in evidence],
                "context_revision": request.constraints.get("context_revision"),
            },
        )

        logger.info(
            "Finished agent run",
            extra={
                "request_id": request.request_id,
                "agent_name": self.agent_name,
                "status": response.status,
                "decision": response.decision.decision,
            },
        )

        return response

    def _gather_evidence(self, request: AgentRequest) -> list[EvidenceItem]:
        symbol = request.payload.get("symbol", "EURUSD")
        snapshot = get_market_snapshot(symbol)

        return [
            EvidenceItem(
                source="market_snapshot",
                description=f"Market snapshot for {symbol}",
                value=snapshot,
            )
        ]

    async def _run_llm_analysis(
        self,
        request: AgentRequest,
        context: AgentContext,
        evidence: list[EvidenceItem],
    ) -> LLMAnalysis | None:
        session_id = context.session_id or str(uuid4())

        await self.session_service.create_session(
            app_name=self.app_name,
            user_id=request.user_id,
            session_id=session_id,
            state={
                "request_id": request.request_id,
                "agent_name": self.agent_name,
            },
        )

        prompt = f'''
Analyze the following HaruQuant task.

Task:
{request.task}

Payload:
{json.dumps(request.payload, indent=2)}

Evidence:
{json.dumps([e.model_dump() for e in evidence], indent=2)}

Return:
- summary
- observations
- risks
- suggestions

Do not make the final decision.
'''

        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        final_text_parts: list[str] = []

        async for event in self.runner.run_async(
            user_id=request.user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text_parts.append(part.text)

        raw_output = "\n".join(final_text_parts).strip()

        return LLMAnalysis(
            summary=raw_output[:1000] if raw_output else "No LLM analysis returned.",
            observations=[],
            risks=[],
            suggestions=[],
            raw_model_output=raw_output,
        )
```

Service rules:

- The service is the public interface.
- The service returns `AgentResponse`.
- The service handles evidence gathering.
- The service handles optional LLM analysis.
- The service calls the deterministic policy.
- The service logs start and finish.
- The service writes audit metadata.
- The service does not make itself chat-visible. Planner and CEOChatGateway decide when specialist output is used in chat.

---

## 14. Evaluator

Each agent must define its own pass/fail checks.

```python
# agents/research/market_intelligence_agent/evaluator.py

from agents._shared.base_contracts import AgentResponse, AgentStatus


def evaluate_response(response: AgentResponse) -> dict:
    checks = {
        "has_request_id": bool(response.request_id),
        "has_agent_name": response.agent_name == "market_intelligence_agent",
        "has_decision": bool(response.decision.decision),
        "has_reasons": len(response.decision.reasons) > 0,
        "status_valid": response.status in AgentStatus,
        "has_audit": bool(response.audit),
    }

    passed = all(checks.values())

    return {
        "passed": passed,
        "checks": checks,
    }
```

Evaluation rules:

- Every agent must have deterministic quality checks.
- Evaluation must check the response envelope.
- Evaluation must check whether the agent violated permissions.
- Evaluation must check whether a final decision exists.
- Evaluation must check audit metadata.
- For trading-critical agents, evaluation must include risk and rejection tests.

---

## 15. Standard README Template

Every agent must include a README.

````md
# Market Intelligence Agent

## Purpose

Analyzes market context and identifies market risk conditions.

## Department

Research Department

## Inputs

- symbol
- timeframe
- market data snapshot
- optional news context

## Outputs

- evidence
- LLM analysis
- deterministic decision
- audit metadata

## Allowed Actions

- summarize_market_context
- flag_news_risk
- flag_spread_risk
- flag_volatility_risk

## Forbidden Actions

- place_trade
- approve_trade
- size_position
- override_risk_governor
- execute_order

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`.

## Tools

- get_market_snapshot

## Tests

Run:

```bash
pytest agents/research/market_intelligence_agent/tests/
```
````

---

## 16. Standard Permissions Model

Each agent must declare what it can and cannot do.

Example:

```python
AGENT_PERMISSIONS = {
    "can_read_market_data": True,
    "can_read_portfolio": False,
    "can_generate_strategy": False,
    "can_backtest": False,
    "can_review_risk": False,
    "can_plan_execution": False,
    "can_execute_trade": False,
    "can_modify_database": False,
}
```

Recommended HaruQuant permission law:

```text
Only Execution Bridge can talk to MT5/cTrader.
Only Risk Governor can approve risk.
Only CEO/Orchestrator can coordinate cross-department workflows.
No specialist agent can directly execute trades.
```

Agent-specific examples:

| Agent                        | Can Execute Trades? | Can Approve Risk? | Can Generate Strategy? | Can Read Portfolio? |
| ---------------------------- | ------------------: | ----------------: | ---------------------: | ------------------: |
| Market Intelligence Agent    |                  No |                No |                     No |            Optional |
| Technical Analyst Agent      |                  No |                No |                     No |            Optional |
| Strategy Creator Agent       |                  No |                No |                    Yes |                  No |
| Strategy Coder Agent         |                  No |                No |                    Yes |                  No |
| Backtest Agent               |                  No |                No |                     No |                  No |
| Statistical Validation Agent |                  No |                No |                     No |                  No |
| Risk Reviewer Agent          |                  No |       Review only |                     No |                 Yes |
| Hard-Coded Risk Governor     |                  No |               Yes |                     No |                 Yes |
| Execution Planner Agent      |                  No |                No |                     No |                 Yes |
| MT5/cTrader Execution Bridge |                 Yes |                No |                     No |                 Yes |
| Audit & Compliance Agent     |                  No |                No |                     No |           Read-only |

---

## 17. Standard Output Envelope

Every agent must return this structure:

```json
{
  "request_id": "abc-123",
  "agent_name": "market_intelligence_agent",
  "status": "success",
  "evidence": [],
  "llm_analysis": {
    "summary": "...",
    "observations": [],
    "risks": [],
    "suggestions": []
  },
  "decision": {
    "status": "success",
    "decision": "market_context_review_complete",
    "confidence": "high",
    "risk_level": "low",
    "allowed_actions": [],
    "blocked_actions": [],
    "reasons": []
  },
  "artifacts": {},
  "audit": {
    "agent_name": "market_intelligence_agent",
    "policy_version": "deterministic_policy_v1",
    "prompt_version": "market_intelligence_agent_prompt_v1",
    "llm_used": true,
    "tools_used": ["get_market_snapshot"],
    "permission_profile": "research_read_only_v1",
    "evidence_refs": ["market_snapshot"],
    "context_revision": "ctx-...",
    "model_provider": "configured_runtime",
    "model_name": "from_HARUQUANT_AGENT_MODEL",
    "fallback_used": false
  }
}
```

This output envelope is what allows Planner, CEOAgent, and CEOChatGateway to consume specialist outputs without needing to understand each internal implementation.

---

## 18. Standard Logging Requirements

Every agent must log:

```text
request_id
agent_name
start_time
end_time
input_validation_status
tools_called
evidence_count
llm_used
deterministic_policy_version
decision
risk_level
allowed_actions
blocked_actions
error_if_any
context_revision
evidence_refs
permission_profile
model_provider
model_name
fallback_used
```

Recommended logger helper:

```python
# agents/_shared/logging.py

from __future__ import annotations

import logging


def get_agent_logger(agent_name: str) -> logging.Logger:
    logger = logging.getLogger(f"haruquant.agents.{agent_name}")
    logger.setLevel(logging.INFO)
    return logger
```

---

## 19. Standard Audit Requirements

Every agent response must include an `audit` dictionary.

Minimum audit fields:

```json
{
  "agent_name": "market_intelligence_agent",
  "prompt_version": "market_intelligence_agent_prompt_v1",
  "policy_version": "deterministic_policy_v1",
  "llm_used": true,
  "tools_called": ["get_market_snapshot"],
  "permission_profile": "research_read_only_v1",
  "context_revision": "ctx-...",
  "evidence_refs": ["market_snapshot"],
  "model_provider": "configured_runtime",
  "model_name": "from_HARUQUANT_AGENT_MODEL",
  "fallback_used": false
}
```

Audit rules:

- Audit must be machine-readable.
- Audit must include prompt version.
- Audit must include deterministic policy version.
- Audit must include whether LLM was used.
- Audit must include tools called.
- Audit must include permission profile.
- Audit must include context revision when the agent used page or workflow context.
- Audit must include evidence references that CEOAgent can cite in the final memo.
- Audit must include provider/model/fallback fields when optional LLM reasoning was attempted.
- Audit must not include secrets.

---

## 20. Standard Callback Strategy

Later, add runtime callbacks globally for debugging, lifecycle control, policy enforcement, and audit capture. If an agent uses Google ADK, ADK callbacks can implement this layer. If an agent uses the HaruQuant runtime/model adapter, implement the same hooks around the shared runtime boundary.

Use callbacks around these points:

```text
Before agent:
- assign trace_id
- validate request
- log input

Before model:
- redact secrets
- block forbidden prompts
- inject system constraints

After model:
- save raw LLM proposal
- validate schema
- detect hallucinated tool references

Before tool:
- check tool permission
- check risk permissions

After tool:
- log tool result
- normalize evidence

After agent:
- write audit trail
- run evaluator
- emit metrics
```

For HaruQuant, callbacks should be used as guardrails, not as hidden business logic. Business logic still belongs in `deterministic_policy.py`.

---

## 21. Standard Test Requirements

Every agent must have these tests:

```text
test_contracts.py
test_deterministic_policy.py
test_service.py
test_agent_smoke.py
```

### `test_contracts.py`

Must validate:

- Valid request schema
- Valid response schema
- Invalid payload rejection
- Missing required fields
- Output can serialize to JSON

### `test_deterministic_policy.py`

Must validate:

- Normal case
- High-risk case
- Missing evidence case
- Edge threshold case
- LLM cannot override deterministic rules

### `test_service.py`

Must validate:

- Service returns `AgentResponse`
- Audit exists
- Evidence exists
- Decision exists
- Allowed actions and blocked actions are populated correctly
- Errors are handled cleanly

### `test_agent_smoke.py`

Must validate:

- LLM agent/runtime wrapper can be constructed when the agent uses optional LLM reasoning
- Agent can receive a simple prompt
- Agent does not crash at runtime

Example deterministic policy test:

```python
# agents/research/market_intelligence_agent/tests/test_deterministic_policy.py

from agents._shared.base_contracts import EvidenceItem, RiskLevel
from agents.research.market_intelligence_agent.deterministic_policy import (
    make_final_decision,
)


def test_high_spread_blocks_execution():
    evidence = [
        EvidenceItem(
            source="market_snapshot",
            description="Test snapshot",
            value={
                "symbol": "EURUSD",
                "spread_pips": 5.0,
                "volatility_state": "normal",
                "news_risk": "low",
            },
        )
    ]

    decision = make_final_decision(evidence=evidence, llm_analysis=None)

    assert decision.risk_level == RiskLevel.HIGH
    assert "trade_execution" in decision.blocked_actions
```

---

## 22. Standard Agent Runner Script

Each agent should include or support a simple standalone runner for local testing.

```python
# scripts/run_market_intelligence_agent.py

import asyncio
from uuid import uuid4

from agents._shared.base_contracts import AgentRequest, AgentContext
from agents.research.market_intelligence_agent.service import (
    MarketIntelligenceAgentService,
)


async def main() -> None:
    service = MarketIntelligenceAgentService()

    request = AgentRequest(
        request_id=str(uuid4()),
        agent_name="market_intelligence_agent",
        task="Analyze current market context for EURUSD.",
        payload={
            "symbol": "EURUSD",
            "timeframe": "H1",
        },
    )

    context = AgentContext(
        session_id="local_test_session",
    )

    response = await service.run(request, context)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 23. Coding Agent Implementation Prompt

Use this prompt whenever you ask another coding agent to create one HaruQuant agent.

```text
You are implementing one HaruQuant agent.

Follow the HaruQuant Agent Template exactly.

Agent name:
<AGENT_NAME>

Department:
<DEPARTMENT_NAME>

Purpose:
<PURPOSE>

Allowed inputs:
<INPUTS>

Allowed tools:
<TOOLS>

Allowed actions:
<ALLOWED_ACTIONS>

Forbidden actions:
<FORBIDDEN_ACTIONS>

Deterministic final decision rules:
<DETERMINISTIC_RULES>

Required folder:
agents/<department>/<agent_name>/

Required files:
- __init__.py
- agent.py
- contracts.py
- prompts.py
- deterministic_policy.py
- tools.py
- service.py
- evaluator.py
- README.md
- tests/test_contracts.py
- tests/test_deterministic_policy.py
- tests/test_service.py
- tests/test_agent_smoke.py

Hard rules:
1. Use Google ADK or the HaruQuant runtime/model adapter for optional LLM reasoning.
2. The LLM may assist with analysis only.
3. Final decision must be made in deterministic_policy.py.
4. All outputs must use Pydantic schemas.
5. No agent may directly execute trades unless it is the Execution Bridge.
6. No agent may approve risk unless it is the Risk Governor.
7. Add logging and audit metadata.
8. Add tests for normal, edge, and rejected cases.
9. Do not invent tools that are not declared.
10. Keep the public service interface stable: service.run(request, context) -> AgentResponse.
11. Do not wire the specialist directly into the chat UI. Register it with Planner and surface it through CEOChatGateway.
12. Any default chat-facing tools must be read-only.

Return the full code file by file.
```

---

## 24. Per-Agent Specification Template

Before implementing any agent, fill this out.

```md
# <Agent Name> Specification

## Department

<Department name>

## Purpose

<What this agent is responsible for>

## Non-Goals

<What this agent must not do>

## Inputs

| Field | Type | Required | Description |
|---|---|---:|---|
| symbol | str | Yes | Trading symbol |
| timeframe | str | No | Analysis timeframe |

## Tools

| Tool | Purpose | Permission Level |
|---|---|---|
| get_market_snapshot | Reads market data | Read-only |

## Evidence Required

- <Evidence item 1>
- <Evidence item 2>

## LLM Responsibilities

- <Allowed LLM responsibility 1>
- <Allowed LLM responsibility 2>

## Deterministic Decision Rules

- Rule 1:
- Rule 2:
- Rule 3:

## Allowed Actions

- <Allowed action 1>
- <Allowed action 2>

## Blocked Actions

- <Blocked action 1>
- <Blocked action 2>

## Output Artifacts

- <Artifact 1>
- <Artifact 2>

## Tests Required

- Normal case
- Missing evidence
- High-risk case
- Rejection case
- LLM override attempt
```

---

## 25. Recommended Build Order

Build the system in this order:

```text
Already built:
1. CEO chat runtime: services/ceo_gateway.py
2. Planner Agent: agents/executive/planner_agent/service.py
3. CEO Agent: agents/executive/ceo_agent/service.py
4. Read-only chat tool executor: agents/runtime/tool_executor.py

Build next:
5. Shared contracts and base agent template
6. Market Intelligence Agent
7. Technical Analyst Agent
8. Strategy Scout Agent
9. Strategy Creator Agent
10. Strategy Coder Agent
11. Strategy Reviewer Agent
12. Backtest Agent
13. Optimization Comparator
14. Robustness / Monte Carlo Agent
15. Statistical Validation Agent
16. Risk Reviewer Agent
17. Portfolio Manager Agent
18. Execution Planner Agent
19. MT5 / cTrader Execution Bridge
20. Performance Reporter
21. Cost Optimizer
22. Audit & Compliance Agent
23. RiskGovernor deterministic service
```

This order keeps the existing CEO chat path stable while each specialist becomes reliable alone before Planner routes work to it.

`RiskGovernor` is listed as a deterministic service, not a normal LLM specialist. It must follow stricter policy-as-code and fail-closed requirements, with no optional LLM decision layer.

---

## 26. Department-Level Guidelines

### Research Department

Agents:

- Market Intelligence Agent
- Strategy Scout Agent
- News & Sentiment Agent
- Technical Analyst Agent

Primary responsibility:

```text
Understand the market, discover opportunities, summarize context, and provide evidence.
```

Hard restrictions:

```text
No trade execution.
No final risk approval.
No portfolio modification.
```

---

### Strategy Development Department

Agents:

- Strategy Creator Agent
- Strategy Coder Agent
- Strategy Reviewer Agent

Primary responsibility:

```text
Create, code, and review trading strategies.
```

Hard restrictions:

```text
No live trade execution.
No risk approval.
No production deployment without validation and risk gating.
```

---

### Validation & Backtesting Department

Agents:

- Backtest Agent
- Optimization Comparator
- Robustness / Monte Carlo Agent
- Statistical Validation Agent

Primary responsibility:

```text
Test whether a strategy is historically valid, statistically stable, and robust.
```

Hard restrictions:

```text
No live trade execution.
No live deployment approval without Risk Governor.
```

---

### Risk & Portfolio Department

Agents:

- Risk Reviewer
- RiskGovernor deterministic service
- Portfolio Manager Agent

Primary responsibility:

```text
Review risk, enforce deterministic risk limits, and assess portfolio-level impact.
```

Hard restrictions:

```text
Only RiskGovernor can approve or reject risk.
Portfolio Manager can propose adjustments but cannot bypass RiskGovernor.
```

---

### Execution Department

Agents/services:

- Execution Planner
- Kill Switch Service
- MT5/cTrader Execution Bridge
- Broker / Exchange

Primary responsibility:

```text
Plan and execute approved trades safely.
```

Hard restrictions:

```text
Execution Bridge may execute only approved orders.
Kill Switch can block execution.
No execution without Risk Governor approval.
```

---

### Operations & Audit Department

Agents:

- Performance Reporter
- Cost Optimizer
- Audit & Compliance Agent

Primary responsibility:

```text
Report, audit, explain, and monitor operational health.
```

Hard restrictions:

```text
No trade execution.
No risk override.
No strategy modification without orchestration approval.
```

---

## 27. Definition of Done for Every Agent

An agent is complete only when:

```text
1. It has the standard folder structure.
2. It has Pydantic input/output contracts.
3. It has an optional LLM runtime factory if it uses LLM reasoning.
4. It has clearly scoped tools.
5. It has a deterministic policy layer.
6. It returns the standard AgentResponse envelope.
7. It has audit metadata.
8. It has unit tests.
9. It has a README.
10. It can run alone without the full multi-agent system.
11. Its output can later be consumed by Planner, CEOAgent, and CEOChatGateway.
```

---

## 28. Final Architecture Rule

The most important architectural decision is this:

```text
Each agent is not just an LLM prompt.
Each agent is a small deterministic service with optional LLM reasoning inside it.
```

That is what will make the full HaruQuant agentic firm testable, debuggable, and safe to expand.

---

## 29. References

The template is aligned with HaruQuant's current CEOChatGateway architecture and can optionally use ADK concepts:

- Google Cloud Agent Development Kit overview: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
- Google ADK documentation repository: https://github.com/google/adk-docs/blob/main/docs/get-started/about.md
- ADK evaluation codelab: https://codelabs.developers.google.com/adk-eval/instructions
- Google Cloud blog on ADK state and memory: https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk
