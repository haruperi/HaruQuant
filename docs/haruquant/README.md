# HaruQuant Docs

Status: canonical index
Scope: directory entry point and navigation
Use this when: you need to find the right document quickly
Owner: platform architecture
Review cadence: on every docs structure change

This directory is the organized documentation root for HaruQuant's agentic and
governed backend_retiring.

Use this file as the entry point instead of browsing the directory tree blind.

Validation script: `python scripts/tools/validate_haruquant_docs.py`

## Start Here

- [Playbook.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\Playbook.md)
- [agents/Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\agents\Catalog.md)
- [workflows/Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\workflows\Catalog.md)
- [tools/Tool_Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\tools\Tool_Catalog.md)

## Folders

### `agents/`

Agent-level documentation.

- agent catalog
- per-agent specifications
- prompts and runtime-facing agent notes

Current key files:

- [agents/Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\agents\Catalog.md)
- [agents/Hypothesis_Designer_Agent.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\agents\Hypothesis_Designer_Agent.md)

### `workflows/`

Workflow catalog and workflow-facing operating docs.

- [workflows/Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\workflows\Catalog.md)

### `tools/`

Tool, MCP resource, and prompt catalogs.

- [tools/Tool_Catalog.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\tools\Tool_Catalog.md)

### `architecture/`

High-level architecture and ADR indexing.

- [architecture/ADR_Index.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\architecture\ADR_Index.md)

### `specs/`

Formal design and system specifications.

- [specs/System_Architecture.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\System_Architecture.md)
- [specs/Requirements.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\Requirements.md)
- [specs/Security.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\Security.md)
- [specs/Observability_Audit.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\Observability_Audit.md)
- [specs/Benchmark_Eval.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\Benchmark_Eval.md)
- [specs/AI_Chatbot_Architecture.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\AI_Chatbot_Architecture.md)
- [specs/AI_Chatbot_Context_Contract.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\AI_Chatbot_Context_Contract.md)
- [specs/AI_Chatbot_Event_Schema.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\specs\AI_Chatbot_Event_Schema.md)

### `governance/`

Approval, escalation, and policy documents.

- [governance/Approval_Standard.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\governance\Approval_Standard.md)
- [governance/Policy_Map.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\governance\Policy_Map.md)
- [governance/AI_Chatbot_Execution_Safety.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\governance\AI_Chatbot_Execution_Safety.md)
- [governance/AI_Chatbot_RBAC_Matrix.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\governance\AI_Chatbot_RBAC_Matrix.md)

### `operations/`

Runbooks and operational acceptance docs.

- [operations/Operations_Runbook.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\operations\Operations_Runbook.md)
- [operations/Shadow_Mode_Acceptance.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\operations\Shadow_Mode_Acceptance.md)
- [operations/runbooks/Incident_Response.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\operations\runbooks\Incident_Response.md)
- [operations/runbooks/Postmortem_Template.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\operations\runbooks\Postmortem_Template.md)

### `plans/`

Implementation plans, migration plans, and project-level planning documents.

- [plans/ND881_Implementation_Plan.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\plans\ND881_Implementation_Plan.md)
- [plans/Lesson_2_Unsupervised_Plan.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\plans\Lesson_2_Unsupervised_Plan.md)
- [plans/Strategy_Catalog_Reconciliation_Plan.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\plans\Strategy_Catalog_Reconciliation_Plan.md)
- [plans/AI_Chatbot_Implementation_Plan.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\plans\AI_Chatbot_Implementation_Plan.md)
- [plans/AI_Chatbot_Conversational_Multi_Agent_Plan.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\plans\AI_Chatbot_Conversational_Multi_Agent_Plan.md)

### `traceability/`

Coverage, checklist, and traceability documents.

- [traceability/AI_Trading_Traceability.md](C:\Users\rharu\Documents\MyApplications\HaruQuant\docs\haruquant\traceability\AI_Trading_Traceability.md)

## Notes

- `Playbook.md` remains at the root because it is the broadest
  top-level guide in this documentation set.
- New agent docs should go under `docs/haruquant/agents/`.
- New workflow docs should go under `docs/haruquant/workflows/`.
- New tool and MCP catalogs should go under `docs/haruquant/tools/`.

## How To Document A New Feature

When a new feature is added to HaruQuant, do not create isolated notes first.
Start by updating the canonical docs that describe how the system now works.

### Documentation rule

Every feature should be documented across three layers:

1. **What changed in the system**
   Update the canonical catalog or spec that now owns the feature.
2. **How the feature works in detail**
   Add or update a focused feature document only if the feature has enough
   implementation, governance, or operational detail to justify it.
3. **How the feature is tracked and operated**
   Update planning, traceability, governance, or runbook docs if the feature
   changes delivery status, approval paths, or operations.

### Required workflow for every new feature

1. Decide the feature type:
   - agent
   - workflow
   - tool or MCP resource
   - platform capability
   - governance or operational capability
2. Update the relevant canonical catalog first:
   - agent -> `docs/haruquant/agents/Catalog.md`
   - workflow -> `docs/haruquant/workflows/Catalog.md`
   - tool/resource/prompt -> `docs/haruquant/tools/Tool_Catalog.md`
   - architecture/spec behavior -> `docs/haruquant/specs/`
   - governance behavior -> `docs/haruquant/governance/`
   - operational behavior -> `docs/haruquant/operations/`
3. Add a focused feature doc when needed:
   - create a new file in the owning folder if the feature has its own rulebook,
     contracts, lifecycle, failure modes, examples, or usage guidance
   - use a concise canonical filename in `Title_Case.md`
4. Update cross-cutting docs if the feature affects them:
   - implementation status -> `docs/haruquant/traceability/AI_Trading_Traceability.md`
   - delivery sequencing or migration -> `docs/haruquant/plans/`
   - approval or policy boundaries -> `docs/haruquant/governance/`
   - runtime and incident handling -> `docs/haruquant/operations/`
   - architecture or requirements -> `docs/haruquant/specs/`
5. Add the new document to this README if it becomes a key entry point.
6. Run `python scripts/tools/validate_haruquant_docs.py`.

### Minimum content standard for a new feature document

If a feature gets its own document, include these fields near the top:

- `Status:`
- `Scope:`
- `Use this when:`
- `Companion docs:`
- `Owner:`
- `Review cadence:`

Then document, as relevant:

- purpose
- inputs and outputs
- dependencies
- workflow placement
- tools/resources/contracts used
- persistence or artifacts created
- governance and approval constraints
- observability and audit expectations
- failure modes
- examples or operator usage

### Consistency rules

- Prefer updating an existing canonical document over creating a duplicate.
- One feature should have one obvious home document.
- Catalogs describe inventory; feature docs describe implementation detail.
- Plans describe intended work; traceability describes current status.
- Runbooks describe operation and recovery, not feature design.
- If a document becomes the new canonical source for a feature, link it from
  this README and the appropriate catalog.
