# AI Chat Page Context Injection

Status: production context contract
Scope: route-aware, compact page context injected into every AI Chat turn

## Versioned Schema

Current schema version: `page_context.v1`

Core fields:

- `context_schema_version`
- `route`
- `page_type`
- `page_title`
- `entity_refs`
- `context_revision`
- `freshness`
- `authority`
- `summary`
- `payload`

## Route Registry

Backend registry: `services/context_builders/__init__.py`

Supported page builders:

- `dashboard`
- `strategy_detail`
- `backtest_detail`
- `optimization_detail`
- `portfolio_risk`
- `live_trading`
- `data_workspace`
- `operator_workflow`
- `generic`

Unsupported pages degrade to `generic` with compact visible state.

## Client Observer

The client context observer lives in:

- `ui/src/providers/PageContextProvider.tsx`
- `ui/src/hooks/usePageContext.ts`

It observes:

- route changes
- registered page context from feature pages
- visible headings, compact text, small table samples, semantic blocks, and actionable controls
- DOM mutations with debounce

## Backend Assembly

Backend assembly lives in:

- `services/context_service.py`
- `services/context/service.py`
- `services/context/builders.py`
- `services/context_builders/*.py`

The assembler:

- infers page type from route and page hints
- chooses a route-specific builder
- compacts DOM snapshots
- limits table rows, columns, semantic blocks, and action elements
- adds freshness and authority markers
- emits a unique `context_revision`

## Guardrails

Raw table dumps are blocked. Builders keep only small samples and record:

```json
{
  "raw_table_dump_blocked": true,
  "table_rows_per_table": 4
}
```

Large payloads are truncated to stay within the context budget.

## Conversation Metadata

Each chat turn stores:

- `context_revision`
- `context_schema_version`
- `context_route`
- `context_page_type`

Thread context metadata updates automatically when route/page context changes.
