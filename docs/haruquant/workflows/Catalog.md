# Workflow Catalog

Status: canonical workflow catalog
Scope: workflow inventory, triggers, contracts, controls, and ownership
Use this when: you need to see how HaruQuant workflows are wired end to end
Companion docs: `../Playbook.md`, `../agents/Catalog.md`, `../tools/Tool_Catalog.md`
Owner: backend platform
Review cadence: on every workflow add/remove/change

| Workflow | Goal | Trigger | Input Schema | Output Schema | Pattern | Agents | Tools/Resources | Policy Checks | Approval Checks | Compensation Design | Observability | Owner | Failure Modes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `trade_execution` | Execute validated trade | Execution intent | `ExecutionIntent` | `ExecutionReceipt` | Sequential + compensation | orchestrator, execution_agent, risk_governor | mt5_mcp, execution service | Risk decision required | Class C/D require human approval | Offset order / close position | Trace + span + cost | trading_team | MT5 down, risk block |
| `research_discovery` | Discover trading edge | Symbol request | `ResearchRequest` | `ResearchResult` | Sequential | research_agent, regime_agent | research_mcp, market_data_mcp | Data access policy | Auto-allowed | N/A (read-only) | Trace + audit | research_team | Insufficient data |
| `portfolio_analysis` | Analyze portfolio risk | Portfolio request | `PortfolioRequest` | `PortfolioSummary` | Parallel | portfolio_agent, exposure_agent, correlation_agent | risk_analytics_mcp, sql_mcp | Read-only data | Auto-allowed | N/A (read-only) | Trace + cost | quant_team | Missing positions |
| `strategy_creation` | Convert rough strategy idea into a governed research asset | Rough strategy idea or AI Chat Strategy Creator tool request | rough human idea or chat prompt | `StrategyBlueprint` plus optional registered strategy artifact | Sequential | strategy_creator_agent, monitoring_agent | strategy design services, strategy catalog, governance registry | Contract validation, rulebook defaults, artifact persistence | Full Permissions required for writes from AI Chat | Stop at research registration, no live mutation | Trace + artifact metadata + governance row | quant_team | vague idea, incomplete methodology, invalid blueprint |
| `strategy_optimization` | Optimize strategy parameters | Optimization request | `OptimizationRequest` | `OptimizationResult` | Evaluator-Optimizer | orchestrator_agent | optimization_mcp, backtest_mcp | Resource limits | Auto-allowed | Abort run | Trace + cost | quant_team | Timeout, OOM |
| `risk_governance` | Gate trade on risk | Trade proposal | `RiskAssessmentRequest` | `RiskAssessmentDecision` | Sequential | risk_governor_agent | risk_engine, policy_service | All risk policies | Class D to human approval | Reject trade | Trace + audit | risk_team | Policy misconfig |
| `market_monitor` | Monitor market conditions | Scheduled | `MonitoringQuery` | `MonitoringResult` | Parallel | monitoring_agent, regime_agent | sql_mcp, market_data_mcp | Read-only | Auto-allowed | N/A | Trace | platform_team | Data gap |
| `simulation_backtest` | Run config-driven simulation backtest | UI/API/example config | `SimulationConfig` | `SimulationRunResult` | Sequential | N/A | simulation config, strategy registry, data preparer, vectorized/event-driven simulator | Read-only market data | Auto-allowed | N/A | Result metadata + logs | quant_team | Missing data, invalid config, strategy error |
