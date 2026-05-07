# Strategy Hypothesis Agent

## Purpose

Converts vetted research ideas into testable strategy hypotheses with acceptance and rejection criteria.

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
- `strategy_hypothesis_report` artifact

## Allowed Actions

- `create_strategy_hypothesis`
- `define_acceptance_criteria`
- `define_rejection_criteria`
- `save_strategy_hypothesis`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `retrieve_candidate_ideas`
- `build_hypothesis_contract`
- `save_strategy_hypothesis_report`

## Tests

Run:

```bash
pytest agents/research/strategy_hypothesis_agent/tests/
```
