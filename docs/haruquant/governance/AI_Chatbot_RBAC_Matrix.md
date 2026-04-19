# HaruQuant AI Chatbot RBAC Matrix

Status: canonical feature RBAC policy
Scope: chatbot entitlements by user role, capability tier, and approval path
Use this when: you need to know which chatbot capabilities each role may access
Companion docs: `AI_Chatbot_Execution_Safety.md`, `../specs/AI_Chatbot_Architecture.md`, `../plans/AI_Chatbot_Implementation_Plan.md`
Owner: security and compliance owner with product owner
Review cadence: on every entitlement change

## Purpose

This document defines the role-based entitlement matrix for the HaruQuant AI
chatbot.

## Capability Classes

- `chat.basic`
- `chat.read_only_tools`
- `chat.retrieval`
- `chat.signal_proposals`
- `chat.action_drafts`
- `chat.paper_execution_review`
- `chat.paper_execution_approve`
- `chat.admin_controls`

## Role Matrix

| Role | Basic Chat | Read-Only Tools | Retrieval | Signal Proposals | Action Drafts | Paper Execution Review | Paper Execution Approve | Admin Controls |
|---|---|---|---|---|---|---|---|---|
| Viewer | yes | yes | yes | no | no | no | no | no |
| Research Analyst | yes | yes | yes | yes | no | no | no | no |
| Quant Researcher | yes | yes | yes | yes | yes | no | no | no |
| Trader | yes | yes | yes | yes | yes | yes | no | no |
| Risk Officer | yes | yes | yes | yes | yes | yes | yes | no |
| Operator | yes | yes | yes | no | yes | yes | no | yes |
| Platform Admin | yes | yes | yes | no | no | no | no | yes |

## Interpretation Rules

- role permission is necessary but not sufficient; policy checks still apply
- page or entity access must also be satisfied before context is assembled
- higher-trust capabilities must emit stronger audit trails
- approve authority must remain distinct from generate authority where possible

## Approval Model

| Capability | Requires Approval | Notes |
|---|---|---|
| Basic chat | no | standard authenticated use |
| Read-only tools | no | must still pass allowlist and entitlement checks |
| Signal proposals | no | proposals only, no execution |
| Action drafts | yes | human confirmation required |
| Paper execution approve | yes | restricted to approved roles and governed mode |
| Admin controls | yes | operationally sensitive actions |

## Initial Enforcement Requirements

- all requests tied to authenticated user identity
- entitlements resolved server-side
- frontend may hide controls, but backend is the enforcement point
- blocked entitlements must emit policy events

## Review Triggers

Re-review this matrix when:

- a new chatbot capability class is introduced
- a role is added or changed
- a phase expands from read-only to draft or paper-automation behavior
- audit or compliance requirements change
