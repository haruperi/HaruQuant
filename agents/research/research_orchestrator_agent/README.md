# Research Department Orchestrator Agent

## Purpose

Coordinates research agents, merges findings, resolves conflicts, and prepares final research packages.

## Department

Research Department

## Inputs

- symbol or symbols
- timeframe or timeframes
- data_window
- research_question
- context_revision
- evidence_refs

## Outputs

- evidence
- optional LLM analysis proposal
- deterministic decision
- audit metadata
- `research_orchestration_report` artifact

## Allowed Actions

- `create_research_plan`
- `route_research_tasks`
- `merge_research_reports`
- `resolve_research_conflicts`
- `produce_final_research_package`
- `save_research_package`
- `handoff_approved_hypothesis`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `call_research_agent_services`
- `retrieve_evidence_memory`
- `save_research_package`

## Tests

Run:

```bash
pytest agents/research/research_orchestrator_agent/tests/
```
