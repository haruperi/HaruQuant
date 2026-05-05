

## Policy tools
tools/policy_tools.py
Contains:
read_constitution()
read_risk_policy()
read_agent_permissions()
read_strategy_lifecycle_policy()
validate_against_constitution()
validate_against_risk_policy()
validate_agent_permission()


Used by:
CEO Agent
Planner Agent
Orchestrator
Risk Reviewer
Audit Agent


---
## Task tools
tools/task_tools.py
Contains:
create_agent_task()
assign_agent_task()
start_agent_task()
complete_agent_task()
fail_agent_task()
block_agent_task()
create_child_task()
get_task_tree()
get_task_status()
list_active_tasks()


Used by:
CEO Agent
Planner Agent
Conversation Orchestrator
Task Manager
Audit Agent


---
## Memory and evidence tools
tools/memory_tools.py
Contains:
create_evidence_ref()
read_evidence_ref()
list_evidence_refs()
save_research_report()
read_research_report()
save_strategy_memory()
read_strategy_memory()
save_performance_memory()
read_performance_memory()
save_lesson_learned()
search_institutional_memory()
search_strategy_memory()
search_simulation_memory()
verify_evidence_integrity()

Used by almost all agents.

---
## Data tools
tools/data_tools.py
Contains:
list_symbols()
get_symbol_metadata()
get_ohlcv_data()
get_tick_data()
get_spread_history()
get_session_calendar()
get_economic_calendar()
get_high_impact_news_events()
get_latest_price()
get_latest_tick()
get_data_freshness()
validate_data_quality()
detect_missing_bars()
detect_duplicate_ticks()
detect_bad_spreads()
normalize_symbol_data()

Used by:
Research Agent
Market Intelligence Agent
Technical Analyst Agent
Simulation Agent
RiskGovernor
Prop Firm Compliance Agent
Execution Planner

---
## Research tools
tools/research_tools.py
Contains:
create_market_intelligence_report()
create_technical_analysis_report()
create_strategy_idea()
score_strategy_idea()
rank_strategy_ideas()
search_internal_research()
search_external_research()
summarize_research_source()
create_bull_case()
create_bear_case()
create_research_debate_summary()

Used by:
Research Agent
Market Intelligence Agent
Strategy Scout Agent
Technical Analyst Agent
Bull Researcher
Bear Researcher


---

## Strategy tools
tools/strategy_tools.py
Contains:
create_strategy_spec()
read_strategy_spec()
update_strategy_spec()
validate_strategy_spec()
reject_strategy_spec()
approve_strategy_spec_for_code_review()
create_strategy_version()
compare_strategy_versions()
set_strategy_lifecycle_state()
request_strategy_promotion()
request_strategy_demotion()
request_strategy_retirement()

Used by:
Strategy Creator Agent
Strategy Spec Validator Agent
Strategy Reviewer Agent
Portfolio Manager Agent
CEO Agent

---
## Code tools
tools/code_tools.py
Contains:
generate_strategy_code()
read_strategy_code()
save_strategy_code()
update_strategy_code()
generate_strategy_tests()
run_strategy_unit_tests()
run_strategy_static_checks()
run_lookahead_bias_check()
run_repainting_check()
run_parameter_sanity_check()
create_strategy_code_hash()
lock_strategy_code_version()

Used by:
Strategy Codegen Agent
Strategy Test Generator Agent
Strategy Reviewer Agent
Audit Agent

---
## Simulation tools
tools/simulation_tools.py
Contains:
create_simulation_request()
run_simulation()
cancel_simulation()
read_simulation_result()
list_simulation_runs()
compare_simulation_runs()
save_simulation_config()
save_simulation_trades()
save_simulation_orders()
save_simulation_deals()
save_simulation_equity_curve()
save_simulation_metrics()
create_simulation_report()
lock_simulation_result()


Used by:
Simulation Agent
Simulation Analyst Agent
Risk Reviewer Agent
CEO Agent

---
## Analytics tools
tools/analytics_tools.py
Contains wrappers around your analytics stack:

calculate_trade_metrics()
calculate_return_metrics()
calculate_drawdown_metrics()
calculate_ratio_metrics()
calculate_risk_metrics()
calculate_efficiency_metrics()
calculate_distribution_metrics()
calculate_benchmark_metrics()
run_statistical_tests()
calculate_long_short_split()
calculate_session_performance()
calculate_monthly_performance()
calculate_regime_performance()
calculate_cost_sensitivity()


Used by:
Simulation Agent
Simulation Analyst Agent
Risk Reviewer Agent
Statistical Validation Agent
Performance Reporter Agent

---
## Risk tools
tools/risk_tools.py
Contains:


get_account_snapshot()
get_open_positions()
get_pending_orders()
calculate_position_risk()
calculate_trade_risk()
calculate_portfolio_exposure()
calculate_symbol_exposure()
calculate_currency_cluster_exposure()
calculate_usd_cluster_exposure()
calculate_correlation_matrix()
calculate_correlation_impact()
calculate_margin_impact()
calculate_var()
calculate_cvar()
check_daily_loss_limit()
check_total_loss_limit()
check_portfolio_drawdown_limit()
request_risk_approval()
approve_trade_proposal()
reject_trade_proposal()
issue_risk_approval_token()
revoke_risk_approval_token()


Used by:
RiskGovernor
Risk Reviewer Agent
Execution Planner Agent
Portfolio Manager Agent
Audit Agent

The actual deterministic logic should live in:
services/risk/governor.py

The tool is just the interface.

---
## Prop-firm compliance tools
tools/prop_firm_tools.py
Contains:

check_prop_firm_daily_loss()
check_prop_firm_total_loss()
check_prop_firm_profit_target()
check_prop_firm_news_window()
check_prop_firm_weekend_rule()
check_prop_firm_overnight_rule()
check_forbidden_practices()
check_ea_automation_compliance()
check_allocation_compliance()
calculate_consistency_score()
check_best_day_rule_threshold()
create_prop_firm_compliance_report()


Used by:


Prop Firm Compliance Agent
RiskGovernor
Consistency Rule Agent
Audit Agent
Execution Planner


The real logic should live in:
services/risk/prop_firm_compliance.py


---
## Paper execution tools
tools/paper_execution_tools.py
Contains:
start_paper_trading()
stop_paper_trading()
place_paper_order()
close_paper_position()
cancel_paper_order()
get_paper_account_snapshot()
get_paper_positions()
get_paper_trade_log()
simulate_spread()
simulate_slippage()
simulate_commission()
simulate_swap()
Used by:
Paper Execution Agent
RiskGovernor
Performance Reporter
Audit Agent


Real logic lives in:
services/execution/paper_broker.py


---
## Live execution tools
tools/live_execution_tools.py
Contains:
request_live_activation()
activate_live_trading()
deactivate_live_trading()
create_trade_proposal()
create_execution_plan()
validate_execution_plan()
place_live_order()
close_live_position()
cancel_live_order()
modify_live_order()
Used by:
Execution Planner Agent
Live Execution Agent
RiskGovernor
Order Router
Audit Agent

## Broker tools
tools/broker_tools.py
Contains:
mt5_get_account_info()
mt5_get_symbol_info()
mt5_get_latest_tick()
mt5_get_positions()
mt5_get_orders()
mt5_place_order()
mt5_close_position()
mt5_cancel_order()
mt5_modify_order()

ctrader_get_account_info()
ctrader_get_symbol_info()
ctrader_get_latest_tick()
ctrader_get_positions()
ctrader_get_orders()
ctrader_place_order()
ctrader_close_position()
ctrader_cancel_order()
ctrader_modify_order()
Real logic lives in:
services/execution/mt5_bridge.py
execution/ctrader_bridge.py


Agents should not call broker bridge functions directly. They should call controlled execution tools, which then verify permissions, approvals, and RiskGovernor tokens.

---

## Kill switch tools
tools/kill_switch_tools.py
Contains:
check_kill_switch_status()
trigger_kill_switch()
clear_kill_switch()
pause_all_trading()
pause_new_entries()
flatten_all_positions()
disable_strategy_execution()

Real logic lives in:
services/risk/kill_switch.py

---
## Reporting tools
tools/reporting_tools.py
Contains:
create_daily_report()
create_weekly_report()
create_monthly_report()
create_board_report()
create_strategy_report()
create_simulation_report()
create_risk_report()
create_compliance_report()
create_audit_report()
export_report_markdown()
export_report_pdf()
read_report()
list_reports()

Used by:
Performance Reporter Agent
CEO Agent
Audit Agent
Board Liaison Agent


---

## Audit tools


tools/audit_tools.py
Contains:
append_audit_log()
read_audit_log()
verify_audit_chain()
verify_tool_call_logged()
verify_trade_has_risk_approval()
verify_strategy_lifecycle_compliance()
verify_no_forbidden_tool_use()
verify_no_policy_file_tampering()
create_audit_finding()
escalate_audit_finding()
lock_audit_record()

Used by every agent.


---
# ✅ Correct approach: Define contract, build incrementally

# 1. Start with a unified tool registry.

# The registry contains metadata about every tool, including:

# tool name
# description (must match agent instructions)
# input/output schemas
# allowed agents
# risk_level (read_only, write, critical)
# requires_audit
# requires_risk_governor
# requires_human_approval
# enabled status
# 2. Implement only the tools you need for the current vertical slice.

# 3. For each tool, implement:

# The "public" tool interface (wrapper for agents)
# The "internal" implementation
# Guardrails and safety checks
# Audit logging integration
# RiskGovernor integration
# 4. Use a contract-first approach:

# Define the tool in one place (tool registry).
# Update agent instructions to reflect the exact tool description and behavior.
# Update the internal implementation when needed, but keep the contract the same.
# This allows you to add tools incrementally without breaking existing agents.
