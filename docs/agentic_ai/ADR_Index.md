# ADR Index (Playbook §25)

## Template

```
Title: <decision title>
Status: Accepted | Deprecated | Superseded by ADR-XXX
Date: YYYY-MM-DD
Context: <what led to this decision>
Decision: <what we decided>
Consequences: <what happens as a result>
Alternatives Considered: <what else we looked at>
Follow-up: <actions to take>
```

## Decisions

| # | Title | Status | Date | Follow-up |
|---|---|---|---|---|
| 001 | Use ADK for reasoning/orchestration | Accepted | 2024-01-01 | Evaluate new ADK versions quarterly |
| 002 | Use MCP for external capability boundaries | Accepted | 2024-01-01 | Add new MCP servers per domain |
| 003 | Split backend/services/ from apps/ | Accepted | 2024-01-01 | Complete — apps/ deleted |
| 004 | stdio transport for local MCP servers | Accepted | 2024-01-01 | Evaluate HTTP for production deployment |
| 005 | SQLite for persistence during migration | Accepted | 2024-01-01 | Evaluate PostgreSQL for production scale |
| 006 | Separate risk_engine from risk control plane | Accepted | 2024-06-01 | Monitor for divergence |
| 007 | Flatten backend/api/legacy to backend/api/ | Accepted | 2024-06-01 | Monitor route organization |
| 008 | Centralize agent model config in agent_model.py | Accepted | 2024-12-01 | Support per-agent model overrides |
| 009 | Gemini 3.1 Flash Lite as default agent model | Accepted | 2024-12-01 | Benchmark against alternatives quarterly |

---

## ADR-008: Centralize Agent Model Configuration

**Status:** Accepted
**Date:** 2024-12-01
**Context:** Agent model names were scattered across agent definition files, making model switches error-prone and inconsistent.
**Decision:** Centralize all agent model configuration in `backend/config/agent_model.py` with `AGENT_MODEL` as the single source of truth, environment variable override support, and model tier routing.
**Consequences:** Changing `AGENT_MODEL` updates all agents instantly. Environment variable `HARUQUANT_AGENT_MODEL` allows runtime override without code changes.
**Alternatives Considered:** Per-agent model strings (rejected — too scattered); config file only (rejected — no env override).
**Follow-up:** Support per-agent model overrides via agent-specific config.

## ADR-009: Gemini 3.1 Flash Lite as Default

**Status:** Accepted
**Date:** 2024-12-01
**Context:** Need a default model balancing cost, latency, and quality for all agents.
**Decision:** `gemini-3.1-flash-lite-preview` is the default for all agents, with `gemini-3.1-pro` as the premium tier for complex reasoning.
**Consequences:** Low per-request cost, good latency. Premium tier available for quality-critical workflows.
**Alternatives Considered:** GPT-4o (higher cost), local llama/ollama (higher latency, lower quality), Claude (API dependency).
**Follow-up:** Benchmark against open-weight models quarterly.
