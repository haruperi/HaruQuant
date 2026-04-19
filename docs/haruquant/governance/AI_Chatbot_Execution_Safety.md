# HaruQuant AI Chatbot Execution Safety

Status: canonical feature safety policy
Scope: action boundaries, tool permission tiers, and non-bypass rules for the chatbot
Use this when: you need the approved safety constraints for what the chatbot may read, propose, draft, or execute
Companion docs: `AI_Chatbot_RBAC_Matrix.md`, `../specs/AI_Chatbot_Architecture.md`, `../specs/AI_Chatbot_Event_Schema.md`, `../plans/AI_Chatbot_Implementation_Plan.md`
Owner: security and compliance owner with quant/risk lead
Review cadence: before every phase that expands authority

## Purpose

This document defines the hard safety boundary for the HaruQuant AI chatbot.

## Non-Negotiable Rules

- free-form chat may not directly place live trades
- direct broker invocation from conversational output is prohibited
- all tool calls must pass allowlist policy and entitlement checks
- action creation is separate from action approval
- action approval is separate from action execution
- all action attempts must be auditable
- live execution authority is out of scope until explicitly approved in future
  governance

## Tool Permission Tiers

| Tier | Name | Description | Allowed in Chat |
|---|---|---|---|
| T1 | Read-Only | data lookup, summaries, diagnostics, retrieval | yes |
| T2 | Simulated | paper-only or analytical simulation capabilities | only in explicitly governed modes |
| T3 | Draft Action | create structured drafts for human review | only with approval workflow |
| T4 | Live Action | live broker or irreversible mutations | no |

## Allowed Behaviors By Phase

| Phase Band | Allowed Capability |
|---|---|
| 0-5 | read-only answer generation with grounded tools |
| 6-7 | domain-aware explanations, comparisons, diagnostics |
| 8 | structured signal proposals only |
| 9 | supervised action drafts with approval gating |
| 10 | governed paper automation only |
| 11-13 | no expansion of live-action authority unless separately approved |

## Mandatory Safeguards

- RBAC and entitlement validation
- tool allowlist enforcement
- risk pre-check before action draft creation
- immutable audit event emission
- duplicate side-effect protection on retry or regenerate
- policy block response surfaced clearly to user
- kill-switch support for any paper-automation mode

## Prohibited Shortcuts

- no hidden action-taking tools in general chat mode
- no “assistant convenience” bypass around approval UI
- no reliance on conversational memory as sufficient authority for execution
- no use of ungrounded model text as an execution command

## Required User-Facing Disclosures

- read-only grounded answer
- tool used or data source used
- signal proposal only, not executed
- action requires approval
- blocked by policy

## Approval Gate For Authority Expansion

The chatbot may only expand from one authority band to the next when:

- prior phase acceptance criteria are met
- audit visibility exists
- entitlement model is tested
- security and compliance sign off
- quant/risk sign off
- rollback path exists

## Acceptance Conditions

- safety boundary is explicit and testable
- live broker mutation from free-form chat is impossible by design
- all authority-expanding phases have approval checkpoints
