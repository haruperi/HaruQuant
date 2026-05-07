# Research Validation Agent

## Purpose

Challenges research conclusions, checks evidence quality, bias risk, missing evidence, and handoff readiness.

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
- `research_validation_report` artifact

## Allowed Actions

- `validate_research_evidence`
- `assign_validation_status`
- `block_weak_hypotheses`
- `save_validation_result`
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

- `retrieve_research_reports`
- `check_evidence_quality`
- `check_bias_risks`
- `save_research_validation_report`

## Tests

Run:

```bash
pytest agents/research/research_validation_agent/tests/
```
