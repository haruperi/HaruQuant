"""Materialize StrategyBlueprint contracts into catalog and governance records."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from contracts.strategy_blueprint.model import StrategyBlueprint, StrategyBlueprintPayload
from services.strategy.catalog import (
    StrategyCatalogCreateRequest,
    StrategyCatalogService,
)

from .blueprint_renderer import StrategyBlueprintRenderer
from .blueprint_validator import StrategyBlueprintValidator


@dataclass(frozen=True)
class StrategyBlueprintMaterializationRequest:
    blueprint: StrategyBlueprint
    user_id: int
    description: str | None = None
    category: str | None = None


@dataclass(frozen=True)
class StrategyBlueprintMaterializationResult:
    strategy: dict[str, Any]
    blueprint_artifact_path: str
    metadata_artifact_path: str


class StrategyBlueprintMaterializationService:
    """Register blueprint-driven strategies through the existing catalog flow."""

    def __init__(
        self,
        *,
        catalog_service: StrategyCatalogService,
        renderer: StrategyBlueprintRenderer | None = None,
        validator: StrategyBlueprintValidator | None = None,
    ) -> None:
        self._catalog_service = catalog_service
        self._renderer = renderer or StrategyBlueprintRenderer()
        self._validator = validator or StrategyBlueprintValidator()

    def materialize(
        self,
        request: StrategyBlueprintMaterializationRequest,
    ) -> StrategyBlueprintMaterializationResult:
        validation = self._validator.validate(
            request.blueprint.model_dump(mode="json"),
            source_idea=request.blueprint.payload.source_idea,
        )
        blueprint = validation.blueprint
        payload = blueprint.payload
        rendered_code = self._renderer.render_python_strategy(blueprint)

        strategy = self._catalog_service.create_strategy(
            StrategyCatalogCreateRequest(
                name=payload.strategy_name,
                description=request.description or payload.source_idea,
                category=request.category or payload.strategy_type,
                code=rendered_code,
                parameters=self._parameters_from_payload(payload),
                parameter_types=self._parameter_types_from_payload(payload),
                symbol=self._symbol_from_payload(payload),
                timeframe=payload.asset_scope.timeframe,
                strategy_type=payload.strategy_type,
                money_management=self._money_management_from_payload(payload),
                variables=self._variables_from_payload(payload),
                variable_types=self._variable_types_from_payload(payload),
            ),
            user_id=request.user_id,
        )

        active_file_path = Path(str(strategy["active_file_path"]))
        metadata_path = active_file_path.parent / "metadata.json"
        blueprint_path = active_file_path.parent / "strategy_blueprint.json"

        blueprint_path.write_text(
            json.dumps(blueprint.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "blueprintArtifactPath": str(blueprint_path),
                "blueprintSummary": self._renderer.render_summary(blueprint),
                "backtestReadiness": payload.backtest_readiness,
                "assumptionsApplied": payload.assumptions_applied,
                "assumptionDefaultsUsed": payload.assumption_defaults_used,
            }
        )
        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        strategy = self._catalog_service.get_strategy(int(strategy["id"]), user_id=request.user_id)
        return StrategyBlueprintMaterializationResult(
            strategy=strategy,
            blueprint_artifact_path=str(blueprint_path),
            metadata_artifact_path=str(metadata_path),
        )

    def _symbol_from_payload(self, payload: StrategyBlueprintPayload) -> str | None:
        if len(payload.asset_scope.assets) == 1:
            return payload.asset_scope.assets[0]
        return None

    def _parameters_from_payload(self, payload: StrategyBlueprintPayload) -> dict[str, Any]:
        parameters: dict[str, Any] = {
            "assets": payload.asset_scope.assets,
            "timeframe": payload.asset_scope.timeframe,
            "data_granularity": payload.asset_scope.data_granularity,
            "entry_logic": payload.entry_logic,
            "exit_logic": payload.exit_logic,
            "stop_loss": payload.risk_management.stop_loss,
            "take_profit": payload.risk_management.take_profit,
            "ignore_stop_loss_take_profit": payload.risk_management.ignore_stop_loss_take_profit,
            "position_sizing": payload.position_sizing.sizing_rule,
            "leverage": payload.position_sizing.leverage,
        }
        if payload.model_spec is not None:
            parameters["model_spec"] = payload.model_spec.model_dump(mode="json")
        if payload.portfolio_construction is not None:
            parameters["portfolio_construction"] = payload.portfolio_construction.model_dump(mode="json")
        return parameters

    def _parameter_types_from_payload(self, payload: StrategyBlueprintPayload) -> dict[str, str]:
        parameter_types = {
            "assets": "list[str]",
            "timeframe": "str",
            "data_granularity": "str",
            "entry_logic": "list[str]",
            "exit_logic": "list[str]",
            "stop_loss": "str|None",
            "take_profit": "str|None",
            "ignore_stop_loss_take_profit": "bool",
            "position_sizing": "str",
            "leverage": "float",
        }
        if payload.model_spec is not None:
            parameter_types["model_spec"] = "dict"
        if payload.portfolio_construction is not None:
            parameter_types["portfolio_construction"] = "dict"
        return parameter_types

    def _money_management_from_payload(self, payload: StrategyBlueprintPayload) -> dict[str, Any]:
        return {
            "stop_loss": payload.risk_management.stop_loss,
            "take_profit": payload.risk_management.take_profit,
            "additional_rules": payload.risk_management.additional_rules,
            "position_sizing": payload.position_sizing.sizing_rule,
            "leverage": payload.position_sizing.leverage,
        }

    def _variables_from_payload(self, payload: StrategyBlueprintPayload) -> dict[str, Any]:
        variables: dict[str, Any] = {
            "strategy_id": payload.strategy_id,
            "render_target": payload.render_target,
            "backtest_readiness": payload.backtest_readiness,
        }
        if payload.model_spec is not None:
            variables["model_type"] = payload.model_spec.model_type
            variables["prediction_horizon"] = payload.model_spec.prediction_horizon
        if payload.portfolio_construction is not None:
            variables["portfolio_method"] = payload.portfolio_construction.method
            variables["rebalance_frequency"] = payload.portfolio_construction.rebalance_frequency
        return variables

    def _variable_types_from_payload(self, payload: StrategyBlueprintPayload) -> dict[str, str]:
        variable_types = {
            "strategy_id": "str",
            "render_target": "str",
            "backtest_readiness": "str",
        }
        if payload.model_spec is not None:
            variable_types["model_type"] = "str"
            variable_types["prediction_horizon"] = "str"
        if payload.portfolio_construction is not None:
            variable_types["portfolio_method"] = "str"
            variable_types["rebalance_frequency"] = "str"
        return variable_types

