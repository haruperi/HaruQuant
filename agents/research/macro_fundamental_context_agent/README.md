# Macro and Fundamental Context Agent

## Purpose

Analyzes macro, fundamental, central-bank, rate, inflation, growth, and event context.

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
- `macro_fundamental_report` artifact

## Allowed Actions

- `summarize_macro_context`
- `classify_macro_regime`
- `flag_macro_event_risk`
- `save_macro_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `get_macro_calendar`
- `get_fundamental_snapshot`
- `get_rate_policy_context`
- `save_macro_fundamental_report`

## Tests

Run:

```bash
pytest agents/research/macro_fundamental_context_agent/tests/
```
