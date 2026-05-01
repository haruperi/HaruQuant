"""Strategy Creator agent and materialization service."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from backend.contracts.strategy_blueprint.model import StrategyBlueprint
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.strategy.catalog import StrategyCatalogService
from backend.services.strategy.design import (
    StrategyBlueprintMaterializationRequest,
    StrategyBlueprintMaterializationService,
    StrategyBlueprintRenderer,
    StrategyBlueprintValidator,
)

from .prompts.strategy_creator_template import STRATEGY_CREATOR_AGENT_INSTRUCTION


@dataclass(frozen=True)
class StrategyCreatorResult:
    blueprint: StrategyBlueprint | None
    rendered_code: str
    metadata_preview: dict[str, Any]
    validation_issues: tuple[str, ...]
    code_valid: bool
    materialized: bool
    needs_clarification: bool = False
    needs_confirmation: bool = False
    workflow_stage: str = "generate"
    missing_inputs: tuple[str, ...] = ()
    clarification_question: str | None = None
    final_interpretation: dict[str, Any] | None = None
    artifact: dict[str, Any] | None = None
    indicator_artifacts: tuple[dict[str, Any], ...] = ()
    strategy: dict[str, Any] | None = None
    blueprint_artifact_path: str | None = None
    metadata_artifact_path: str | None = None
    permission_note: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "blueprint": self.blueprint.model_dump(mode="json") if self.blueprint is not None else None,
            "artifact": self.artifact,
            "indicator_artifacts": list(self.indicator_artifacts),
            "metadata_preview": self.metadata_preview,
            "validation_issues": list(self.validation_issues),
            "code_valid": self.code_valid,
            "materialized": self.materialized,
            "needs_clarification": self.needs_clarification,
            "needs_confirmation": self.needs_confirmation,
            "workflow_stage": self.workflow_stage,
            "missing_inputs": list(self.missing_inputs),
            "clarification_question": self.clarification_question,
            "final_interpretation": self.final_interpretation,
            "strategy": self.strategy,
            "blueprint_artifact_path": self.blueprint_artifact_path,
            "metadata_artifact_path": self.metadata_artifact_path,
            "permission_note": self.permission_note,
        }


class StrategyCreatorAgent:
    """Create StrategyBlueprint artifacts and optionally register strategies."""

    agent_name = "strategy_creator_agent"
    instruction = STRATEGY_CREATOR_AGENT_INSTRUCTION

    def __init__(
        self,
        *,
        db_manager: DatabaseManager | None = None,
        validator: StrategyBlueprintValidator | None = None,
        renderer: StrategyBlueprintRenderer | None = None,
        materializer: StrategyBlueprintMaterializationService | None = None,
        indicator_base_dir: Path | str | None = None,
    ) -> None:
        self.db_manager = db_manager or DatabaseManager()
        self.validator = validator or StrategyBlueprintValidator()
        self.renderer = renderer or StrategyBlueprintRenderer()
        self.materializer = materializer or StrategyBlueprintMaterializationService(
            catalog_service=StrategyCatalogService(db_manager=self.db_manager),
            renderer=self.renderer,
            validator=self.validator,
        )
        self.indicator_base_dir = Path(indicator_base_dir or "backend/services/indicators")

    def create_from_idea(
        self,
        *,
        user_id: int,
        idea: str,
        context: dict[str, object] | None = None,
        full_permissions: bool = False,
    ) -> StrategyCreatorResult:
        context = context or {}
        confirmed = self._is_confirmation_prompt(idea)
        source_idea = self._source_idea_for_request(idea=idea, context=context, confirmed=confirmed)
        intake = self._analyze_intake(idea=source_idea, context=context, full_permissions=full_permissions)
        if intake:
            return StrategyCreatorResult(
                blueprint=None,
                rendered_code="",
                metadata_preview={},
                validation_issues=(),
                code_valid=False,
                materialized=False,
                needs_clarification=True,
                workflow_stage="clarify",
                missing_inputs=tuple(intake),
                clarification_question=self._clarification_question(intake),
                permission_note="Strategy generation is blocked until the missing strategy inputs are supplied.",
            )

        candidate = self._candidate_from_idea(idea=source_idea, context=context)
        validation = self.validator.validate(candidate, source_idea=source_idea)
        blueprint = validation.blueprint
        final_interpretation = self._final_interpretation(blueprint)
        if not confirmed:
            return StrategyCreatorResult(
                blueprint=blueprint,
                rendered_code="",
                metadata_preview=self._metadata_preview(blueprint),
                validation_issues=tuple(validation.issues),
                code_valid=False,
                materialized=False,
                needs_confirmation=True,
                workflow_stage="confirm",
                final_interpretation=final_interpretation,
                permission_note="Strategy interpretation is ready for review. Confirm or modify before generation.",
            )

        rendered_code = self.renderer.render_python_strategy(blueprint)
        code_valid, code_issue = self._validate_rendered_code(rendered_code)
        issues = tuple([*validation.issues, *([code_issue] if code_issue else [])])
        metadata_preview = self._metadata_preview(blueprint)
        indicator_specs = self._indicator_specs_from_idea(source_idea)
        indicator_artifacts: tuple[dict[str, Any], ...] = ()
        if full_permissions:
            indicator_artifacts = tuple(
                self._materialize_indicator(spec)
                for spec in indicator_specs
                if not spec["available"] and spec["creation_allowed"]
            )
        indicator_issues = tuple(
            f"indicator_{artifact['normalized_name']}={artifact['validation_issue'] or 'not_materialized'}"
            for artifact in indicator_artifacts
            if not artifact.get("materialized")
        )
        issues = tuple([*issues, *indicator_issues])
        artifact = self._artifact(
            blueprint=blueprint,
            rendered_code=rendered_code,
            validation_issues=issues,
            indicator_specs=indicator_specs,
            indicator_artifacts=indicator_artifacts,
        )

        if not full_permissions:
            return StrategyCreatorResult(
                blueprint=blueprint,
                rendered_code=rendered_code,
                metadata_preview=metadata_preview,
                validation_issues=issues,
                code_valid=code_valid,
                materialized=False,
                workflow_stage="generate",
                final_interpretation=final_interpretation,
                artifact=artifact,
                indicator_artifacts=indicator_artifacts,
                permission_note="Strategy artifact generated only. Attach Full Permissions with Strategy Creator to write strategy.py, metadata.json, and database records.",
            )

        if not code_valid:
            return StrategyCreatorResult(
                blueprint=blueprint,
                rendered_code=rendered_code,
                metadata_preview=metadata_preview,
                validation_issues=issues,
                code_valid=False,
                materialized=False,
                workflow_stage="generate",
                final_interpretation=final_interpretation,
                artifact=artifact,
                indicator_artifacts=indicator_artifacts,
                permission_note="Full Permissions was attached, but persistence was blocked because generated code failed validation.",
            )

        if indicator_issues:
            return StrategyCreatorResult(
                blueprint=blueprint,
                rendered_code=rendered_code,
                metadata_preview=metadata_preview,
                validation_issues=issues,
                code_valid=code_valid,
                materialized=False,
                workflow_stage="generate",
                final_interpretation=final_interpretation,
                artifact=artifact,
                indicator_artifacts=indicator_artifacts,
                permission_note="Full Permissions was attached, but strategy persistence was blocked because required indicator creation failed validation.",
            )

        materialized = self.materializer.materialize(
            StrategyBlueprintMaterializationRequest(
                blueprint=blueprint,
                user_id=user_id,
                description=blueprint.payload.source_idea,
                category=blueprint.payload.strategy_type,
            )
        )
        artifact = self._mark_artifact_saved(artifact, materialized.strategy)
        return StrategyCreatorResult(
            blueprint=blueprint,
            rendered_code=rendered_code,
            metadata_preview=metadata_preview,
            validation_issues=issues,
            code_valid=code_valid,
            materialized=True,
            workflow_stage="generate",
            final_interpretation=final_interpretation,
            artifact=artifact,
            indicator_artifacts=indicator_artifacts,
            strategy=materialized.strategy,
            blueprint_artifact_path=materialized.blueprint_artifact_path,
            metadata_artifact_path=materialized.metadata_artifact_path,
            permission_note="Full Permissions granted. Strategy was registered through the standard strategy catalog pipeline.",
        )

    @staticmethod
    def _mark_artifact_saved(artifact: dict[str, Any], strategy: dict[str, Any]) -> dict[str, Any]:
        updated = dict(artifact)
        updated["saved_strategy"] = {
            "id": strategy.get("id"),
            "active_version": strategy.get("active_version"),
            "active_file_path": strategy.get("active_file_path"),
        }
        actions = []
        for action in artifact.get("available_actions", []):
            next_action = dict(action)
            if next_action.get("id") == "save_draft_strategy":
                next_action["enabled"] = False
                next_action["reason"] = "Already saved in the strategy catalog."
            if next_action.get("id") == "export":
                next_action["enabled"] = True
                next_action["reason"] = "Saved strategies can be exported from the strategy editor."
            actions.append(next_action)
        updated["available_actions"] = actions
        return updated

    def _source_idea_for_request(self, *, idea: str, context: dict[str, object], confirmed: bool) -> str:
        if not confirmed:
            prior_user_text = self._recent_user_strategy_text(context)
            if prior_user_text:
                return f"{prior_user_text}\n{idea}".strip()
            return idea
        prior_user_text = self._recent_user_strategy_text(context)
        return prior_user_text or idea

    @staticmethod
    def _recent_user_strategy_text(context: dict[str, object]) -> str:
        raw_messages = context.get("strategy_creator_recent_messages")
        if not isinstance(raw_messages, list):
            return ""
        user_messages: list[str] = []
        for item in raw_messages[-8:]:
            if not isinstance(item, dict):
                continue
            if item.get("role") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                user_messages.append(content.strip())
        return "\n".join(user_messages)

    @staticmethod
    def _is_confirmation_prompt(idea: str) -> bool:
        lower = idea.strip().lower()
        confirmations = (
            "confirm",
            "confirmed",
            "yes generate",
            "generate it",
            "go ahead",
            "looks good",
            "proceed",
            "create it",
            "save it",
            "use this",
        )
        return any(token in lower for token in confirmations)

    @staticmethod
    def _final_interpretation(blueprint: StrategyBlueprint) -> dict[str, Any]:
        payload = blueprint.payload
        return {
            "strategy_type": payload.strategy_type,
            "assets": payload.asset_scope.assets,
            "timeframe": payload.asset_scope.timeframe,
            "entry_logic": payload.entry_logic,
            "exit_logic": payload.exit_logic,
            "risk_management": payload.risk_management.model_dump(mode="json"),
            "position_sizing": payload.position_sizing.model_dump(mode="json"),
            "model_spec": payload.model_spec.model_dump(mode="json") if payload.model_spec is not None else None,
            "portfolio_construction": (
                payload.portfolio_construction.model_dump(mode="json")
                if payload.portfolio_construction is not None
                else None
            ),
            "other_assumptions": payload.assumptions_applied,
        }

    def _analyze_intake(self, *, idea: str, context: dict[str, object], full_permissions: bool) -> list[str]:
        missing: list[str] = []
        if not (self._extract_symbol(idea) or self._context_str(context, "symbol")):
            missing.append("instrument_or_market")
        if not (self._extract_timeframe(idea) or self._context_str(context, "timeframe")):
            missing.append("timeframe")
        if not self._has_entry_rule(idea):
            missing.append("entry_rule")
        if not self._has_exit_rule(idea):
            missing.append("exit_rule")
        if not self._has_risk_rule(idea):
            missing.append("risk_rule")
        if not self._has_position_sizing(idea):
            missing.append("position_sizing")
        missing_indicator_specs = [spec for spec in self._indicator_specs_from_idea(idea) if not spec["available"]]
        if missing_indicator_specs and not any(spec["creation_allowed"] for spec in missing_indicator_specs):
            missing.append("indicator_creation_permission")
        if missing_indicator_specs and any(spec["creation_allowed"] for spec in missing_indicator_specs) and not full_permissions:
            missing.append("full_permissions_for_indicator_creation")
        if any(spec["needs_definition"] for spec in missing_indicator_specs):
            missing.append("indicator_formula_or_definition")
        return missing

    @staticmethod
    def _clarification_question(missing: list[str]) -> str:
        labels = {
            "instrument_or_market": "instrument or market",
            "timeframe": "timeframe",
            "entry_rule": "entry rule",
            "exit_rule": "exit rule",
            "risk_rule": "risk rule",
            "position_sizing": "position sizing",
            "indicator_creation_permission": "permission to create missing custom indicator files",
            "full_permissions_for_indicator_creation": "Full Permissions tool for indicator file creation",
            "indicator_formula_or_definition": "indicator formula or calculation definition",
        }
        requested = ", ".join(labels[item] for item in missing)
        return (
            "I need the following before I can generate a complete HaruQuant strategy: "
            f"{requested}. Please provide them in one message."
        )

    def _indicator_specs_from_idea(self, idea: str) -> list[dict[str, Any]]:
        available = self._available_indicator_names()
        specs: list[dict[str, Any]] = []
        for indicator in self._requested_indicators(idea):
            normalized = self._normalize_indicator_name(indicator)
            is_available = normalized in available
            specs.append(
                {
                    "name": indicator,
                    "normalized_name": normalized,
                    "available": is_available,
                    "category": self._indicator_category(normalized),
                    "creation_allowed": self._indicator_creation_allowed(idea),
                    "needs_definition": not is_available and not self._can_generate_known_indicator(normalized, idea),
                    "target_path": str(self.indicator_base_dir / "custom" / f"{normalized}.py"),
                }
            )
        return specs

    def _available_indicator_names(self) -> set[str]:
        names = {
            "rsi",
            "ema",
            "sma",
            "wma",
            "atr",
            "bbands",
            "bollinger_bands",
            "accumulation_distribution",
            "currency_strength",
            "smc",
            "hurst",
        }
        if self.indicator_base_dir.exists():
            for path in self.indicator_base_dir.rglob("*.py"):
                if path.name == "__init__.py" or path.name == "indicator_template.py":
                    continue
                names.add(path.stem.lower())
        return names

    @staticmethod
    def _requested_indicators(idea: str) -> list[str]:
        lower = idea.lower()
        aliases = {
            "rsi": ("rsi", "relative strength index"),
            "ema": ("ema", "exponential moving average"),
            "sma": ("sma", "simple moving average"),
            "wma": ("wma", "weighted moving average"),
            "atr": ("atr", "average true range"),
            "bbands": ("bbands", "bollinger", "bollinger bands"),
            "supertrend": ("supertrend", "super trend"),
            "vwap": ("vwap", "volume weighted average price"),
            "keltner_channel": ("keltner", "keltner channel"),
            "donchian_channel": ("donchian", "donchian channel"),
        }
        requested: list[str] = []
        for canonical, tokens in aliases.items():
            if any(token in lower for token in tokens):
                requested.append(canonical)
        for match in re.findall(r"\b(?:indicator|using|with)\s+([A-Za-z][A-Za-z0-9 _-]{2,32})", idea, flags=re.IGNORECASE):
            candidate = re.sub(r"\b(strategy|entry|exit|signal|filter|and|with|using)\b", " ", match, flags=re.IGNORECASE).strip()
            if candidate:
                requested.append(candidate)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in requested:
            normalized = StrategyCreatorAgent._normalize_indicator_name(item)
            if normalized not in seen:
                deduped.append(item)
                seen.add(normalized)
        return deduped

    @staticmethod
    def _normalize_indicator_name(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
        aliases = {
            "bollinger": "bbands",
            "bollinger_bands": "bbands",
            "super_trend": "supertrend",
            "volume_weighted_average_price": "vwap",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _indicator_category(normalized_name: str) -> str:
        if normalized_name in {"rsi"}:
            return "momentum"
        if normalized_name in {"ema", "sma", "wma", "supertrend", "vwap"}:
            return "trend"
        if normalized_name in {"atr", "bbands", "keltner_channel", "donchian_channel"}:
            return "volatility"
        return "custom"

    @staticmethod
    def _indicator_creation_allowed(idea: str) -> bool:
        lower = idea.lower()
        return any(
            token in lower
            for token in (
                "create indicator",
                "create the indicator",
                "also create indicator",
                "also create the indicator",
                "create missing indicator",
                "yes create",
                "generate indicator",
            )
        )

    @staticmethod
    def _can_generate_known_indicator(normalized_name: str, idea: str) -> bool:
        if normalized_name == "supertrend":
            return True
        lower = idea.lower()
        return "formula:" in lower or "calculation:" in lower or "definition:" in lower

    def _candidate_from_idea(self, *, idea: str, context: dict[str, object]) -> dict[str, Any]:
        symbol = self._extract_symbol(idea) or self._context_str(context, "symbol")
        timeframe = self._extract_timeframe(idea) or self._context_str(context, "timeframe")
        payload: dict[str, Any] = {
            "source_idea": idea.strip(),
            "strategy_name": self._strategy_name_from_idea(idea),
            "entry_logic": self._entry_logic_from_idea(idea),
            "exit_logic": self._exit_logic_from_idea(idea),
            "risk_management": {},
        }
        if symbol or timeframe:
            payload["asset_scope"] = {
                "assets": [symbol] if symbol else None,
                "timeframe": timeframe,
                "data_granularity": timeframe,
            }
            payload["asset_scope"] = {
                key: value for key, value in payload["asset_scope"].items() if value
            }
        return {
            "originator": {"type": "agent", "id": self.agent_name},
            "payload": payload,
        }

    @staticmethod
    def _strategy_name_from_idea(idea: str) -> str:
        cleaned = re.sub(r"\b(create|build|make|strategy|for|using|with)\b", " ", idea, flags=re.IGNORECASE)
        words = re.findall(r"[A-Za-z0-9]+", cleaned)[:6]
        return " ".join(word.capitalize() for word in words) + " Strategy" if words else "AI Created Strategy"

    @staticmethod
    def _entry_logic_from_idea(idea: str) -> list[str]:
        lower = idea.lower()
        if "rsi" in lower:
            return [
                "Enter LONG when previous-bar RSI is below 30 and price confirms mean-reversion setup.",
                "Enter SHORT when previous-bar RSI is above 70 and short trades are enabled.",
            ]
        if "mean reversion" in lower or "mean-reversion" in lower:
            return [
                "Enter LONG when price closes below its rolling mean by the configured threshold and starts reverting upward.",
                "Enter SHORT when price closes above its rolling mean by the configured threshold and starts reverting downward.",
            ]
        if "trend" in lower or "moving average" in lower or "ema" in lower:
            return [
                "Enter LONG when the fast moving average crosses above the slow moving average using previous-bar values.",
                "Enter SHORT when the fast moving average crosses below the slow moving average using previous-bar values.",
            ]
        return ["Enter when the objective signal rules derived from the source idea are confirmed on the previous completed bar."]

    @staticmethod
    def _exit_logic_from_idea(idea: str) -> list[str]:
        lower = idea.lower()
        if "rsi" in lower or "mean reversion" in lower or "mean-reversion" in lower:
            return [
                "Exit LONG when RSI normalizes above 50, mean reversion completes, or risk rules trigger.",
                "Exit SHORT when RSI normalizes below 50, mean reversion completes, or risk rules trigger.",
            ]
        if "trend" in lower or "moving average" in lower or "ema" in lower:
            return [
                "Exit LONG when the fast moving average crosses back below the slow moving average or risk rules trigger.",
                "Exit SHORT when the fast moving average crosses back above the slow moving average or risk rules trigger.",
            ]
        return ["Exit when the entry thesis is invalidated or the configured risk rule triggers."]

    @staticmethod
    def _has_entry_rule(idea: str) -> bool:
        lower = idea.lower()
        return any(token in lower for token in ("enter", "buy", "sell", "long", "short", "rsi", "ema", "sma", "macd", "supertrend", "breakout", "cross", "mean reversion", "trend"))

    @staticmethod
    def _has_exit_rule(idea: str) -> bool:
        lower = idea.lower()
        return any(token in lower for token in ("exit", "close", "take profit", "tp", "stop", "stop-loss", "stop loss", "trailing", "when rsi", "supertrend flips", "crosses back"))

    @staticmethod
    def _has_risk_rule(idea: str) -> bool:
        lower = idea.lower()
        return any(token in lower for token in ("stop", "stop-loss", "stop loss", "take profit", "tp", "risk", "drawdown", "no leverage", "leverage"))

    @staticmethod
    def _has_position_sizing(idea: str) -> bool:
        lower = idea.lower()
        return any(token in lower for token in ("position", "size", "sizing", "risk 1", "risk 2", "% risk", "percent risk", "full capital", "equal weight", "lots", "lot"))

    @staticmethod
    def _extract_symbol(idea: str) -> str | None:
        for token in re.findall(r"\b[A-Z]{2,8}\b", idea):
            if token not in {"RSI", "EMA", "SMA", "ATR", "MACD"}:
                return token
        return None

    @staticmethod
    def _extract_timeframe(idea: str) -> str | None:
        match = re.search(r"\b(M1|M5|M15|M30|H1|H4|D1|W1|MN1|1D)\b", idea.upper())
        return match.group(1) if match else None

    @staticmethod
    def _context_str(context: dict[str, object], key: str) -> str | None:
        value = context.get(key)
        return str(value).upper() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _validate_rendered_code(code: str) -> tuple[bool, str | None]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"syntax_error={exc.msg}"
        has_strategy_class = any(isinstance(node, ast.ClassDef) for node in tree.body)
        if not has_strategy_class:
            return False, "missing_strategy_class"
        required_methods = {"on_init", "on_bar", "get_signal"}
        found_methods = {
            child.name
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            for child in node.body
            if isinstance(child, ast.FunctionDef)
        }
        missing = sorted(required_methods - found_methods)
        if missing:
            return False, f"missing_methods={','.join(missing)}"
        banned_imports = {"os", "subprocess", "socket", "requests", "shutil", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
                blocked = sorted(imported & banned_imports)
                if blocked:
                    return False, f"banned_imports={','.join(blocked)}"
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in banned_imports:
                    return False, f"banned_imports={root}"
            if isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                if call_name in {"open", "eval", "exec", "compile", "__import__"}:
                    return False, f"banned_operation={call_name}"
        return True, None

    def _materialize_indicator(self, spec: dict[str, Any]) -> dict[str, Any]:
        normalized_name = str(spec["normalized_name"])
        code = self._render_indicator_code(spec)
        code_valid, issue = self._validate_indicator_code(code, normalized_name)
        artifact = {
            "name": spec["name"],
            "normalized_name": normalized_name,
            "category": spec["category"],
            "code_valid": code_valid,
            "validation_issue": issue,
            "file_path": str(spec["target_path"]),
            "python_indicator_script": code,
            "materialized": False,
        }
        if not code_valid:
            return artifact

        target_path = Path(str(spec["target_path"]))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(code, encoding="utf-8")
        init_path = target_path.parent / "__init__.py"
        self._ensure_custom_indicator_export(init_path=init_path, function_name=normalized_name)
        artifact["materialized"] = True
        return artifact

    @staticmethod
    def _ensure_custom_indicator_export(*, init_path: Path, function_name: str) -> None:
        if not init_path.exists():
            init_path.write_text('"""Custom indicators module."""\n\n__all__ = []\n', encoding="utf-8")
        content = init_path.read_text(encoding="utf-8")
        import_line = f"from backend.services.indicators.custom.{function_name} import {function_name}"
        if import_line not in content:
            content = content.rstrip() + f"\n{import_line}\n"
        if "__all__" in content:
            pattern = r"__all__\s*=\s*\[(?P<body>.*?)\]"
            match = re.search(pattern, content, flags=re.DOTALL)
            if match and f'"{function_name}"' not in match.group("body") and f"'{function_name}'" not in match.group("body"):
                body = match.group("body").rstrip()
                separator = "\n" if body else "\n"
                next_body = f'{body}{separator}    "{function_name}",\n'
                content = content[: match.start("body")] + next_body + content[match.end("body") :]
        else:
            content = content.rstrip() + f'\n\n__all__ = ["{function_name}"]\n'
        init_path.write_text(content, encoding="utf-8")

    def _render_indicator_code(self, spec: dict[str, Any]) -> str:
        normalized_name = str(spec["normalized_name"])
        if normalized_name == "supertrend":
            return self._render_supertrend_indicator()
        return self._render_formula_indicator(normalized_name)

    @staticmethod
    def _render_supertrend_indicator() -> str:
        return '''"""SuperTrend indicator."""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
    require_columns,
    require_dataframe,
    require_positive_float,
    require_positive_int,
)


def supertrend(
    data: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> pd.DataFrame:
    """Compute the SuperTrend trend-following indicator.

    SuperTrend uses ATR-adjusted bands around the median price. Price above the
    active band indicates an uptrend, while price below it indicates a downtrend.
    """
    require_dataframe(data)
    require_positive_int(period, name="period")
    require_positive_float(multiplier, name="multiplier")
    require_columns(data, ("high", "low", "close"))

    logger.debug(f"Calculating SuperTrend with period={period}, multiplier={multiplier}")
    result = data.copy()
    high = result["high"]
    low = result["low"]
    close = result["close"]

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    final_upper = upper_band.copy()
    final_lower = lower_band.copy()
    direction = pd.Series(1, index=result.index, dtype="int64")
    supertrend_values = pd.Series(index=result.index, dtype="float64")

    for index in range(1, len(result)):
        prev = index - 1
        if upper_band.iloc[index] < final_upper.iloc[prev] or close.iloc[prev] > final_upper.iloc[prev]:
            final_upper.iloc[index] = upper_band.iloc[index]
        else:
            final_upper.iloc[index] = final_upper.iloc[prev]

        if lower_band.iloc[index] > final_lower.iloc[prev] or close.iloc[prev] < final_lower.iloc[prev]:
            final_lower.iloc[index] = lower_band.iloc[index]
        else:
            final_lower.iloc[index] = final_lower.iloc[prev]

        if close.iloc[index] > final_upper.iloc[prev]:
            direction.iloc[index] = 1
        elif close.iloc[index] < final_lower.iloc[prev]:
            direction.iloc[index] = -1
        else:
            direction.iloc[index] = direction.iloc[prev]

        supertrend_values.iloc[index] = final_lower.iloc[index] if direction.iloc[index] == 1 else final_upper.iloc[index]

    trend_col = f"supertrend_{period}_{multiplier:g}"
    direction_col = f"supertrend_direction_{period}_{multiplier:g}"
    result[trend_col] = supertrend_values.ffill()
    result[direction_col] = direction

    logger.success(f"SuperTrend calculation complete: {trend_col}, {direction_col}")
    return result
'''

    @staticmethod
    def _render_formula_indicator(normalized_name: str) -> str:
        return f'''"""Custom {normalized_name} indicator.

Generated from Strategy Creator after the user supplied a custom indicator
definition. Review the formula before using in research.
"""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)


def {normalized_name}(
    data: pd.DataFrame,
    period: int = 14,
    price_col: str = "close",
) -> pd.DataFrame:
    """Compute the custom {normalized_name} indicator."""
    require_dataframe(data)
    require_positive_int(period, name="period")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating {normalized_name} with period={{period}} on column '{{price_col}}'")
    result = data.copy()
    col_name = f"{normalized_name}_{{period}}"
    result[col_name] = result[price_col].rolling(window=period, min_periods=period).mean()
    logger.success(f"{normalized_name} calculation complete: {{col_name}}")
    return result
'''

    @staticmethod
    def _validate_indicator_code(code: str, function_name: str) -> tuple[bool, str | None]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"syntax_error={exc.msg}"
        found_function = any(isinstance(node, ast.FunctionDef) and node.name == function_name for node in tree.body)
        if not found_function:
            return False, f"missing_indicator_function={function_name}"
        banned_imports = {"os", "subprocess", "socket", "requests", "shutil", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
                blocked = sorted(imported & banned_imports)
                if blocked:
                    return False, f"banned_imports={','.join(blocked)}"
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in banned_imports:
                    return False, f"banned_imports={root}"
            if isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                if call_name in {"open", "eval", "exec", "compile", "__import__"}:
                    return False, f"banned_operation={call_name}"
        return True, None

    def _metadata_preview(self, blueprint: StrategyBlueprint) -> dict[str, Any]:
        payload = blueprint.payload
        return {
            "name": payload.strategy_name,
            "description": payload.source_idea,
            "category": payload.strategy_type,
            "parameters": {
                "assets": payload.asset_scope.assets,
                "timeframe": payload.asset_scope.timeframe,
                "entry_logic": payload.entry_logic,
                "exit_logic": payload.exit_logic,
                "stop_loss": payload.risk_management.stop_loss,
                "take_profit": payload.risk_management.take_profit,
            },
            "moneyManagement": {
                "stop_loss": payload.risk_management.stop_loss,
                "take_profit": payload.risk_management.take_profit,
                "position_sizing": payload.position_sizing.sizing_rule,
                "leverage": payload.position_sizing.leverage,
            },
            "variables": {
                "strategy_id": payload.strategy_id,
                "render_target": payload.render_target,
                "backtest_readiness": payload.backtest_readiness,
            },
        }

    def _artifact(
        self,
        *,
        blueprint: StrategyBlueprint,
        rendered_code: str,
        validation_issues: tuple[str, ...],
        indicator_specs: list[dict[str, Any]],
        indicator_artifacts: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        payload = blueprint.payload
        parameter_schema = self._parameter_schema(blueprint)
        required_data_fields = self._required_data_fields(blueprint)
        return {
            "strategy_name": payload.strategy_name,
            "hypothesis": payload.source_idea,
            "market_timeframe_assumptions": {
                "assets": payload.asset_scope.assets,
                "timeframe": payload.asset_scope.timeframe,
                "data_granularity": payload.asset_scope.data_granularity,
                "notes": payload.asset_scope.asset_notes,
            },
            "entry_rules": payload.entry_logic,
            "exit_rules": payload.exit_logic,
            "risk_rules": {
                "stop_loss": payload.risk_management.stop_loss,
                "take_profit": payload.risk_management.take_profit,
                "additional_rules": payload.risk_management.additional_rules,
                "position_sizing": payload.position_sizing.sizing_rule,
                "leverage": payload.position_sizing.leverage,
            },
            "parameters": parameter_schema,
            "python_strategy_script": rendered_code,
            "required_data_fields": required_data_fields,
            "indicator_dependencies": indicator_specs,
            "indicator_artifacts": list(indicator_artifacts),
            "backtest_configuration_suggestion": {
                "symbol": payload.asset_scope.assets[0],
                "timeframe": payload.asset_scope.timeframe,
                "data_fields": required_data_fields,
                "initial_capital": 10000,
                "commission_model": "Use the account default commission/slippage model before comparing results.",
                "minimum_checks": [
                    "in-sample and out-of-sample split",
                    "walk-forward validation where supported",
                    "trade count and drawdown review",
                ],
            },
            "validation_checklist": [
                "Syntax parse passed.",
                "Strategy class exists.",
                "Required methods on_init, on_bar, and get_signal exist.",
                "No banned imports or file/process/network operations detected.",
                *[f"Review issue: {issue}" for issue in validation_issues],
            ],
            "known_failure_modes": self._known_failure_modes(blueprint),
            "available_actions": [
                {
                    "id": "save_draft_strategy",
                    "label": "Save draft strategy",
                    "enabled": False,
                    "requires_tool": "full_permissions",
                    "reason": "Attach Full Permissions with Strategy Creator to persist through the catalog pipeline.",
                },
                {
                    "id": "run_backtest_draft",
                    "label": "Run backtest draft",
                    "enabled": False,
                    "reason": "Backtest draft execution requires the next governed action-draft workflow.",
                },
                {
                    "id": "refine",
                    "label": "Refine",
                    "enabled": True,
                    "reason": "Continue the chat with requested changes.",
                },
                {
                    "id": "export",
                    "label": "Export",
                    "enabled": False,
                    "reason": "Export is enabled after the strategy is saved.",
                },
            ],
            "robustness_warning": (
                "Treat this as a research draft. Do not promote it because one backtest looks good; "
                "check parameter sensitivity, out-of-sample behavior, slippage, spread, and regime dependence."
            ),
        }

    @staticmethod
    def _parameter_schema(blueprint: StrategyBlueprint) -> list[dict[str, Any]]:
        lower = blueprint.payload.source_idea.lower()
        schema = [
            {"name": "timeframe", "default": blueprint.payload.asset_scope.timeframe, "range": None, "description": "Bar timeframe used by the strategy."},
            {"name": "risk_per_trade_pct", "default": 1.0, "range": [0.1, 3.0], "description": "Maximum account risk per trade."},
        ]
        if "rsi" in lower:
            schema.extend(
                [
                    {"name": "rsi_period", "default": 14, "range": [5, 30], "description": "RSI lookback period."},
                    {"name": "rsi_oversold", "default": 30, "range": [10, 45], "description": "Long entry threshold."},
                    {"name": "rsi_overbought", "default": 70, "range": [55, 90], "description": "Short entry threshold."},
                    {"name": "rsi_exit", "default": 50, "range": [40, 60], "description": "Mean-reversion exit level."},
                ]
            )
        if any(token in lower for token in ("trend", "moving average", "ema", "sma")):
            schema.extend(
                [
                    {"name": "fast_ma_period", "default": 20, "range": [5, 50], "description": "Fast moving average period."},
                    {"name": "slow_ma_period", "default": 50, "range": [20, 200], "description": "Slow moving average period."},
                ]
            )
        return schema

    @staticmethod
    def _required_data_fields(blueprint: StrategyBlueprint) -> list[str]:
        fields = ["open", "high", "low", "close", "volume"]
        lower = blueprint.payload.source_idea.lower()
        if "rsi" in lower:
            fields.append("rsi")
        if any(token in lower for token in ("ema", "sma", "moving average", "trend")):
            fields.extend(["fast_moving_average", "slow_moving_average"])
        if "supertrend" in lower or "super trend" in lower:
            fields.extend(["atr", "supertrend", "supertrend_direction"])
        return fields

    @staticmethod
    def _known_failure_modes(blueprint: StrategyBlueprint) -> list[str]:
        lower = blueprint.payload.source_idea.lower()
        modes = [
            "Parameter overfitting to one market period.",
            "Spread, slippage, and commission turning marginal edges negative.",
            "Low trade count creating unreliable performance estimates.",
        ]
        if "rsi" in lower or "mean reversion" in lower:
            modes.append("Mean-reversion entries can keep buying into persistent trends.")
        if any(token in lower for token in ("trend", "moving average", "ema", "sma")):
            modes.append("Trend-following entries can whipsaw in sideways markets.")
        return modes


__all__ = [
    "STRATEGY_CREATOR_AGENT_INSTRUCTION",
    "StrategyCreatorAgent",
    "StrategyCreatorResult",
]
