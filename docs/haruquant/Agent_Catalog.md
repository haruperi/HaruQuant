# Agent Catalog

This catalog now reflects the implemented agent layer exactly as exposed by
[backend/agents/__init__.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\__init__.py).

## Exported Agents

| Agent Name | Public Symbol | Module | Kind | Instruction Source | Enforced Output |
|---|---|---|---|---|---|
| `compliance_agent` | `ComplianceAgentWrapper` | `backend/agents/compliance_agent.py` | LLM wrapper | `COMPLIANCE_AGENT_INSTRUCTION` | `EvaluationReport` |
| `correlation_agent` | `CorrelationAgentWrapper` | `backend/agents/correlation_agent.py` | LLM wrapper | `CORRELATION_AGENT_INSTRUCTION` | `ObservationEvent` |
| `drawdown_agent` | `DrawdownAgentWrapper` | `backend/agents/drawdown_agent.py` | LLM wrapper | `DRAWDOWN_AGENT_INSTRUCTION` | `ObservationEvent` |
| `execution_agent` | `ExecutionAgentWrapper` | `backend/agents/execution_agent.py` | LLM wrapper | `EXECUTION_AGENT_INSTRUCTION` | `ExecutionIntent` |
| `exposure_agent` | `ExposureAgentWrapper` | `backend/agents/exposure_agent.py` | LLM wrapper | `EXPOSURE_AGENT_INSTRUCTION` | `ObservationEvent` |
| `intent_router_agent` | `IntentRouterAgent`, `intent_router_agent` | `backend/agents/intent_router.py` | Router/service | classifier + `RouteDecisionService` | dispatches handler output, no canonical output validator |
| `monitoring_agent` | `MonitoringAgentWrapper` | `backend/agents/monitoring_agent.py` | LLM wrapper | `MONITORING_AGENT_INSTRUCTION` | `IncidentAlert` |
| `orchestrator_agent` | `OrchestratorAgentWrapper` | `backend/agents/orchestrator_agent.py` | LLM wrapper | `ORCHESTRATOR_AGENT_INSTRUCTION` | `WorkflowPlan` |
| `portfolio_agent` | `PortfolioAgentWrapper` | `backend/agents/portfolio_agent.py` | LLM wrapper | `PORTFOLIO_AGENT_INSTRUCTION` | `EvaluationReport` |
| `refine_agent` | `RefineAgentWrapper` | `backend/agents/refine_agent.py` | LLM wrapper | `REFINE_AGENT_INSTRUCTION` | `RefinementReport` |
| `regime_agent` | `RegimeAgentWrapper` | `backend/agents/regime_agent.py` | LLM wrapper | `REGIME_AGENT_INSTRUCTION` | `ObservationEvent` |
| `research_agent` | `ResearchAgentWrapper` | `backend/agents/research_agent.py` | LLM wrapper | `RESEARCH_AGENT_INSTRUCTION` | `ObservationEvent` |
| `risk_governor_agent` | `RiskGovernorAgentAdapter` | `backend/agents/risk_governor_agent.py` | deterministic adapter | no LLM instruction; delegates to `DeterministicRiskService` | `RiskAssessmentDecision` |
| `slippage_agent` | `SlippageAgentWrapper` | `backend/agents/slippage_agent.py` | LLM wrapper | `SLIPPAGE_AGENT_INSTRUCTION` | `ObservationEvent` |
| `strategy_agent` | `StrategyAgentWrapper` | `backend/agents/strategy_agent.py` | LLM wrapper | `STRATEGY_AGENT_INSTRUCTION` | `TradeHypothesis` |
| `volatility_agent` | `VolatilityAgentWrapper` | `backend/agents/volatility_agent.py` | LLM wrapper | `VOLATILITY_AGENT_INSTRUCTION` | `ObservationEvent` |

## Notes

- All LLM wrappers are thin adapters over `ADKRunnerService` plus
  `CanonicalOutputValidator`.
- The wrapper input surface is `ADKRunRequest`; the table above records the
  contract each wrapper explicitly validates on output.
- `risk_governor_agent` is not an LLM agent in code. It is a deterministic
  adapter that forwards to a risk service and verifies the returned contract.
- `intent_router_agent` is not an LLM wrapper either. It classifies request
  intent and dispatches to registered handlers.

## Prompt Modules

Prompt-backed agents resolve their instruction strings from
[backend/agents/prompts](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\prompts):

- `compliance_template.py`
- `correlation_template.py`
- `drawdown_template.py`
- `execution_template.py`
- `exposure_template.py`
- `monitoring_template.py`
- `orchestrator_template.py`
- `portfolio_template.py`
- `refine_template.py`
- `regime_template.py`
- `research_template.py`
- `slippage_template.py`
- `strategy_template.py`
- `volatility_template.py`

The deterministic risk governor metadata lives in
[risk_governor_template.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\prompts\risk_governor_template.py).

## Model Configuration

Shared agent model settings are defined in
[backend/config/agent_model.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\config\agent_model.py).

- Default model: `gemini-3.1-flash-lite-preview`
- Override env var: `HARUQUANT_AGENT_MODEL`

## Related Runtime Docs

- [Workflow_Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\Workflow_Catalog.md)
- [Tool_Resource_Prompt_Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\Tool_Resource_Prompt_Catalog.md)
- [backend/agents/runtime](C:\Users\rharu\Documents\MyApplications\HaruQuant\backend\agents\runtime)
