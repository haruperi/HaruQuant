# Evidence Curator Agent

## Purpose

Keeps Research Department evidence memory searchable, auditable, deduplicated, versioned, fresh, and linked.

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
- `evidence_curator_report` artifact

## Allowed Actions

- `save_research_report`
- `save_evidence_ref`
- `deduplicate_evidence`
- `link_evidence`
- `mark_stale`
- `build_evidence_index`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `save_evidence_item`
- `search_evidence_memory`
- `deduplicate_evidence`
- `link_evidence_to_report`
- `mark_evidence_stale`
- `mark_report_superseded`

## Tests

Run:

```bash
pytest agents/research/evidence_curator_agent/tests/
```
