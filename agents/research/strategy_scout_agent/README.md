# Strategy Scout Agent

## Purpose

Discovers candidate strategy ideas from market, technical, historical, and evidence-memory context.

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
- `strategy_scout_report` artifact

## Allowed Actions

- `discover_strategy_ideas`
- `rank_candidate_ideas`
- `reject_weak_ideas`
- `save_strategy_idea_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `search_strategy_memory`
- `retrieve_market_reports`
- `retrieve_technical_reports`
- `score_strategy_ideas`
- `save_strategy_scout_report`

## Tests

Run:

```bash
pytest agents/research/strategy_scout_agent/tests/
```
