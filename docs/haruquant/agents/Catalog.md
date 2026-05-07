# Agent Catalog

Status: canonical agent catalog
Scope: implemented agents, contracts, and operational ownership
Use this when: you need to know what agents exist and what each one emits
Companion docs: `../Playbook.md`, `../workflows/Catalog.md`, `../tools/Tool_Catalog.md`
Owner: backend platform
Review cadence: on every agent add/remove/change

This catalog now reflects the implemented agent layer exactly as exposed by
[agents/__init__.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\canonical HaruQuant packages\agents\__init__.py).

## Exported Agents

| Agent Name | Public Symbol | Module | Kind | Instruction Source | Enforced Output |
|---|---|---|---|---|---|
| `compliance_agent` | `ComplianceAgentWrapper` | `agents/compliance_agent.py` | LLM wrapper | `COMPLIANCE_AGENT_INSTRUCTION` | `EvaluationReport` |
| `correlation_agent` | `CorrelationAgentWrapper` | `agents/correlation_agent.py` | LLM wrapper | `CORRELATION_AGENT_INSTRUCTION` | `ObservationEvent` |
| `drawdown_agent` | `DrawdownAgentWrapper` | `agents/drawdown_agent.py` | LLM wrapper | `DRAWDOWN_AGENT_INSTRUCTION` | `ObservationEvent` |
| `execution_agent` | `ExecutionAgentWrapper` | `agents/execution_agent.py` | LLM wrapper | `EXECUTION_AGENT_INSTRUCTION` | `ExecutionIntent` |
| `exposure_agent` | `ExposureAgentWrapper` | `agents/exposure_agent.py` | LLM wrapper | `EXPOSURE_AGENT_INSTRUCTION` | `ObservationEvent` |
| `strategy_creator_agent` | `StrategyCreatorAgent` | `agents/strategy_creator_agent.py` | deterministic service agent | `STRATEGY_CREATOR_AGENT_INSTRUCTION` | `StrategyBlueprint` plus optional registered strategy artifact |
| `intent_router_agent` | `IntentRouterAgent`, `intent_router_agent` | `agents/intent_router.py` | Router/service | classifier + `RouteDecisionService` | dispatches handler output, no canonical output validator |
| `monitoring_agent` | `MonitoringAgentWrapper` | `agents/monitoring_agent.py` | LLM wrapper | `MONITORING_AGENT_INSTRUCTION` | `IncidentAlert` |
| `orchestrator_agent` | `OrchestratorAgentWrapper` | `agents/orchestrator_agent.py` | LLM wrapper | `ORCHESTRATOR_AGENT_INSTRUCTION` | `WorkflowPlan` |
| `portfolio_agent` | `PortfolioAgentWrapper` | `agents/portfolio_agent.py` | LLM wrapper | `PORTFOLIO_AGENT_INSTRUCTION` | `EvaluationReport` |
| `refine_agent` | `RefineAgentWrapper` | `agents/refine_agent.py` | LLM wrapper | `REFINE_AGENT_INSTRUCTION` | `RefinementReport` |
| `regime_agent` | `RegimeAgentWrapper` | `agents/regime_agent.py` | LLM wrapper | `REGIME_AGENT_INSTRUCTION` | `ObservationEvent` |
| `research_agent` | `ResearchAgentWrapper` | `agents/research_agent.py` | LLM wrapper | `RESEARCH_AGENT_INSTRUCTION` | `ObservationEvent` |
| `risk_governor_agent` | `RiskGovernorAgentAdapter` | `agents/risk_governor_agent.py` | deterministic adapter | no LLM instruction; delegates to `DeterministicRiskService` | `RiskAssessmentDecision` |
| `slippage_agent` | `SlippageAgentWrapper` | `agents/slippage_agent.py` | LLM wrapper | `SLIPPAGE_AGENT_INSTRUCTION` | `ObservationEvent` |
| `strategy_agent` | `StrategyAgentWrapper` | `agents/strategy_agent.py` | LLM wrapper | `STRATEGY_AGENT_INSTRUCTION` | `TradeHypothesis` |
| `volatility_agent` | `VolatilityAgentWrapper` | `agents/volatility_agent.py` | LLM wrapper | `VOLATILITY_AGENT_INSTRUCTION` | `ObservationEvent` |

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

Prompt-backed agents resolve their instruction strings from the `prompts.py`
file inside each canonical agent folder. Shared prompt composition primitives
live in `agents/_shared/prompts.py`.

Examples:

- `agents/executive/ceo_agent/prompts.py`
- `agents/executive/planner_agent/prompts.py`
- `agents/control_plane/prompts.py`
- `agents/strategy_development/strategy_creator_agent/prompts.py`
- `agents/risk_portfolio/portfolio_manager_agent/prompts.py`
- `agents/operations_audit/audit_compliance_agent/prompts.py`

## Model Configuration

Shared agent model settings are defined in
[config/agent_model.py](C:\Users\rharu\Documents\MyApplications\HaruQuant\canonical HaruQuant packages\config\agent_model.py).

- Default model: `gemini-3.1-flash-lite-preview`
- Override env var: `HARUQUANT_AGENT_MODEL`

## Related Runtime Docs

- [Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\workflows\Catalog.md)
- [Tool_Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\tools\Tool_Catalog.md)
- [agents/Strategy_Creator_Agent.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\agents\Strategy_Creator_Agent.md)
- [agents/runtime](C:\Users\rharu\Documents\MyApplications\HaruQuant\canonical HaruQuant packages\agents\runtime)
