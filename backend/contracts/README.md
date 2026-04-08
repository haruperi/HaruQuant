# Canonical Contracts

This directory holds the canonical contract families for the agentic migration.

The governing contract baseline is defined in:
- `docs/agentic_ai/Schemas.md`

This scaffold phase establishes only the repository structure for each contract family.
Contract contents are implemented in later tasks.

## Contract Families

- `workflow_intent`
- `workflow_plan`
- `trade_hypothesis`
- `trade_proposal`
- `risk_assessment_request`
- `risk_assessment_decision`
- `execution_intent`
- `execution_receipt`
- `observation_event`
- `evaluation_report`
- `incident_alert`
- `override_request`
- `override_decision`
- `replay_bundle`

## Standard Package Layout

Each contract family uses the same package shape:

- `schema.json`
- `model.py`
- `README.md`
- `CHANGELOG.md`
- `examples/valid/`
- `examples/invalid/`

This keeps contract discovery and later automation predictable across all families.
