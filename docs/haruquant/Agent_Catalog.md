# Agent Catalog (Playbook §6.3)

| Agent | Purpose | Input Schema | Output Schema | Persona | Model | Tools/Resources | Memory | State Transitions | Policy Profile | Approval Profile | Owner | Benchmark Tasks | Failure Modes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| compliance_agent | Policy compliance check | ComplianceCheckRequest | ComplianceDecision | Compliance Officer | AGENT_MODEL | policy_engine, tool_policy | session | IDLE→CHECKING→PASS/FAIL | Must enforce all policies | Class C/D require approval | risk_team | Pass 10 policy scenarios | Weak policy config |
| correlation_agent | Portfolio correlation analysis | CorrelationRequest | CorrelationResult | Quant Analyst | AGENT_MODEL | risk_analytics_mcp | session | IDLE→ANALYZING→DONE | Read-only data access | Auto-allowed (Class A) | quant_team | Detect correlation > 0.8 | Insufficient data |
| drawdown_agent | Drawdown monitoring | DrawdownRequest | DrawdownResult | Risk Monitor | AGENT_MODEL | risk_analytics_mcp, sql_mcp | session | IDLE→MONITORING→ALERT | Alert on threshold breach | Escalate Class D | risk_team | Detect max DD within 5% | Stale data |
| execution_agent | Trade execution | ExecutionIntent | ExecutionReceipt | Execution Trader | AGENT_MODEL | mt5_mcp, execution_service | session+workflow | IDLE→VALIDATING→EXECUTING→RECEIPT | Require risk decision first | Class C/D require approval | trading_team | Execute order within 5s | MT5 unavailable |
| exposure_agent | Exposure analysis | ExposureRequest | ExposureSummary | Risk Analyst | AGENT_MODEL | risk_analytics_mcp | session | IDLE→CALCULATING→DONE | Read-only | Auto-allowed | risk_team | Calculate exposure within 1% | Missing position data |
| monitoring_agent | Workflow/system monitoring | MonitoringQuery | MonitoringResult | System Operator | AGENT_MODEL | sql_mcp, observability | session | IDLE→QUERYING→REPORTING | Read-only access | Auto-allowed | platform_team | Detect stale workflow | Observability gap |
| orchestrator_agent | Task decomposition & routing | OrchestratorRequest | OrchestratorResult | Orchestrator | AGENT_MODEL | All MCP servers | workflow | IDLE→PLANNING→DISPATCHING→SYNTHESIZING→DONE | Route to correct specialists | Approve task graph | ai_team | Correctly decompose 10 tasks | Ambiguous request |
| portfolio_agent | Portfolio analysis | PortfolioRequest | PortfolioSummary | Portfolio Manager | AGENT_MODEL | risk_analytics_mcp, sql_mcp | session+long-term | IDLE→ANALYZING→REPORTING | Read portfolio state | Auto-allowed | quant_team | Calculate VaR within 5% | Incomplete positions |
| regime_agent | Market regime detection | RegimeRequest | RegimeResult | Macro Analyst | AGENT_MODEL | risk_analytics_mcp, market_data_mcp | session | IDLE→DETECTING→CLASSIFIED | Read market data | Auto-allowed | quant_team | Correct regime 80%+ | Volatile transitions |
| research_agent | Symbol research & edge discovery | ResearchRequest | ResearchResult | Research Analyst | AGENT_MODEL | research_mcp, market_data_mcp | session+long-term | IDLE→RESEARCHING→SYNTHESIZING→DONE | Read-only research | Auto-allowed | research_team | Identify tradeable symbol | Insufficient history |
| risk_governor_agent | Risk governance gate | RiskAssessmentRequest | RiskAssessmentDecision | Risk Governor | AGENT_MODEL | risk_engine, policy_service | session | IDLE→ASSESSING→APPROVE/REJECT/ESCALATE | Enforce all risk policies | Class D → human approval | risk_team | Block 100% of risky trades | Policy misconfig |
| slippage_agent | Slippage analysis | SlippageRequest | SlippageResult | Execution Analyst | AGENT_MODEL | mt5_mcp, sql_mcp | session | IDLE→ANALYZING→REPORTING | Read execution data | Auto-allowed | trading_team | Measure slippage < 1 pip | Missing fill data |
| strategy_agent | Strategy signal generation | StrategyRequest | Signal | Strategy Developer | AGENT_MODEL | strategy_service, market_data_mcp | session+long-term | IDLE→LOADING→SIGNALING→DONE | Load validated strategy only | Auto-allowed | quant_team | Generate correct signal | Strategy error |
| volatility_agent | Volatility analysis | VolatilityRequest | VolatilityResult | Volatility Analyst | AGENT_MODEL | risk_analytics_mcp | session | IDLE→CALCULATING→DONE | Read market data | Auto-allowed | quant_team | Calculate ATR within 5% | Insufficient bars |
| intent_router_agent | Intent classification & dispatch | Request path | RoutingMetadata | Router | AGENT_MODEL | PolicyResolver | none | IDLE→CLASSIFYING→DISPATCHING→DONE | Policy check before dispatch | Block unauthorized | ai_team | Classify 10 intents correctly | Unknown intent |

## Model Configuration

All agents use `AGENT_MODEL = "gemini-3.1-flash-lite-preview"` by default.
To change the model for ALL agents, edit `backend/config/agent_model.py`.
Environment variable `HARUQUANT_AGENT_MODEL` overrides at runtime.
