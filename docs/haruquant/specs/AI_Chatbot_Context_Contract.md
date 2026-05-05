# HaruQuant AI Chatbot Context Contract

Status: canonical feature context contract
Scope: versioned schema and rules for page-aware context injection into the chatbot
Use this when: you need the normalized `page_context` model, precedence rules, and context builder responsibilities
Companion docs: `AI_Chatbot_Architecture.md`, `AI_Chatbot_Event_Schema.md`, `../plans/AI_Chatbot_Implementation_Plan.md`
Owner: backend lead and frontend lead
Review cadence: on every context schema change

## Purpose

This document defines the normalized `page_context` contract used to inject
current HaruQuant page state into the chatbot without conflating that state
with long-term conversation memory.

## Contract Principles

- page context is ephemeral and route-aware
- page context is structured, not free-form prompt text
- page context is compact and token-budgeted
- page context includes freshness and authority markers
- page context must degrade gracefully on unsupported pages
- page context must never dump raw large tables into prompts

## Top-Level Schema

```json
{
  "schema_version": "v1",
  "route": "/strategies/[id]",
  "page_type": "strategy_detail",
  "page_title": "Strategy Detail",
  "entity_refs": [
    {
      "type": "strategy",
      "id": "strategy_123",
      "label": "Mean Reversion Alpha"
    }
  ],
  "context_revision": "ctx_2026_04_19_001",
  "generated_at": "2026-04-19T12:00:00Z",
  "freshness": {
    "observed_at": "2026-04-19T11:59:58Z",
    "staleness_seconds": 2
  },
  "authority": {
    "source": "context_service",
    "trust_level": "system_state"
  },
  "summary": {
    "headline": "Strategy is active in research mode",
    "bullets": [
      "Last backtest completed 15 minutes ago",
      "Current max drawdown 8.2%",
      "Latest optimization run available"
    ]
  },
  "payload": {}
}
```

## Required Fields

- `schema_version`
- `route`
- `page_type`
- `context_revision`
- `generated_at`
- `freshness`
- `authority`
- `summary`
- `payload`

## Page Types

Initial supported page types:

- `dashboard`
- `strategy_detail`
- `backtest_detail`
- `optimization_detail`
- `portfolio_risk`
- `live_trading`
- `data_workspace`
- `operator_workflow`
- `generic`

## Context Builder Responsibilities

Each builder must:

- normalize domain objects into compact summaries
- attach stable entity references
- include freshness markers
- mark data authority source
- respect redaction and entitlement rules
- stay within token and payload budgets

## Precedence Rules

The chatbot must resolve conflicting information in this order:

1. current validated system state from tools and structured context
2. current page context summary and entity references
3. durable pinned facts
4. memory summary
5. recent conversation window
6. older conversational assumptions

## Guardrails

- do not inject raw portfolio tables unless explicitly summarized
- do not inject unbounded logs or report bodies
- do not inject secrets, credentials, or sensitive tokens
- do not include data the current user is not entitled to view
- do not let unsupported routes fail the chat request

## Route-to-Builder Registry

Suggested initial registry:

- dashboard -> `DashboardContextBuilder`
- strategies/[id] -> `StrategyDetailContextBuilder`
- backtests/[id] -> `BacktestDetailContextBuilder`
- optimizations/[id] -> `OptimizationContextBuilder`
- portfolio -> `PortfolioRiskContextBuilder`
- trading/live -> `LiveTradingContextBuilder`
- data -> `DataWorkspaceContextBuilder`
- operator/workflows/[id] -> `OperatorWorkflowContextBuilder`
- fallback -> `GenericContextBuilder`

## Revision and Change Rules

- every schema change must bump `schema_version`
- every assembled context packet must emit a `context_revision`
- incompatible field changes require contract review before deployment

## Acceptance Conditions

- same question can yield different page-relevant answers on different pages
- thread continuity remains intact during route changes
- unsupported pages return a valid generic context packet
- context stays within budget and contains freshness/authority markers
