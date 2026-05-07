# News and Sentiment Agent

## Purpose

Analyzes approved news and sentiment sources and flags event or narrative risk.

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
- `news_sentiment_report` artifact

## Allowed Actions

- `summarize_news_context`
- `classify_sentiment`
- `flag_news_risk`
- `save_sentiment_report`

## Forbidden Actions

- `place_trade`
- `execute_order`
- `approve_risk`
- `modify_portfolio`
- `deploy_strategy`

## Deterministic Policy

Final decisions are made in `deterministic_policy.py`; LLM output is only a proposal.

## Tools

- `get_approved_news_feed`
- `get_sentiment_snapshot`
- `get_economic_calendar`
- `save_news_sentiment_report`

## Tests

Run:

```bash
pytest agents/research/news_sentiment_agent/tests/
```
