# Strategy Creator Agent

This document describes the HaruQuant `strategy_creator_agent`.

The Strategy Creator owns the full path from a fuzzy trading idea to a
HaruQuant strategy artifact. It merges the old hypothesis-design behavior with
the strategy creation pipeline already used by `/strategies`.

## Role

1. Convert rough user intent into a `StrategyBlueprint`.
2. Apply deterministic defaults through `StrategyBlueprintValidator`.
3. Render a `template_strategy.py`-style Python strategy with
   `StrategyBlueprintRenderer`.
4. Validate the rendered code shape before persistence.
5. If and only if the AI Chat request also attaches `Full Permissions`,
   materialize the strategy through `StrategyBlueprintMaterializationService`
   and the existing `StrategyCatalogService`.

Without `Full Permissions`, the agent returns a strategy artifact preview only.
It does not write files, register database records, or mutate the strategy
catalog.

## Source Files

- `backend_retiring/agents/strategy_creator_agent.py`
- `backend_retiring/agents/prompts/strategy_creator_template.py`
- `services/strategy/design/blueprint_validator.py`
- `services/strategy/design/blueprint_renderer.py`
- `services/strategy/design/blueprint_materializer.py`
- `backend_retiring/agents/chat/ai_chat/tool_attachment_registry.py`
- `backend_retiring/agents/chat/ai_chat/ai_gateway.py`

## Persisted Artifacts

When `Strategy Creator` and `Full Permissions` are both attached, the standard
catalog pipeline creates the same artifact family as manual strategy creation:

- `strategy.py`
- `metadata.json`
- `strategy_blueprint.json`
- strategy catalog/database registration
- governance lifecycle registration
