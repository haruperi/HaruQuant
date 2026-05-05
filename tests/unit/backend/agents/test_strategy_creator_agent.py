from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.agents.strategy_creator_agent import StrategyCreatorAgent
from haruquant.strategy import StrategyCatalogService, StrategyStorage
from haruquant.strategy import StrategyBlueprintMaterializationService


COMPLETE_RSI_IDEA = (
    "Create an RSI mean reversion strategy for EURUSD H1. "
    "Enter long when RSI is below 30, exit when RSI recovers above 50, "
    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
)

COMPLETE_SUPERTREND_IDEA = (
    "Create a SuperTrend strategy for EURUSD H1 and also create the indicator. "
    "Enter long when SuperTrend flips bullish, exit when SuperTrend flips bearish, "
    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
)


def _agent(tmp_path: Path) -> StrategyCreatorAgent:
    db_path = tmp_path / "strategy_creator.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    user_id = db.create_user(
        email="creator@example.com",
        username="creator_user",
        password="password",
        full_name="Creator User",
    )
    assert user_id == 1
    catalog = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=GovernanceRepository(db.db_path),
    )
    return StrategyCreatorAgent(
        db_manager=db,
        materializer=StrategyBlueprintMaterializationService(catalog_service=catalog),
        indicator_base_dir=tmp_path / "indicators",
    )


def test_strategy_creator_generates_artifact_without_persistence(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea=COMPLETE_RSI_IDEA,
        full_permissions=False,
    )

    assert result.needs_confirmation is True
    assert result.rendered_code == ""
    assert result.materialized is False

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_RSI_IDEA}]},
        full_permissions=False,
    )

    assert result.needs_clarification is False
    assert result.needs_confirmation is False
    assert result.blueprint.payload.asset_scope.assets == ["EURUSD"]
    assert result.blueprint.payload.asset_scope.timeframe == "H1"
    assert result.code_valid is True
    assert result.materialized is False
    assert result.artifact is not None
    assert result.artifact["required_data_fields"] == ["open", "high", "low", "close", "volume", "rsi"]
    assert result.artifact["known_failure_modes"]
    assert "Full Permissions" in result.permission_note


def test_strategy_creator_materializes_with_full_permissions(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_RSI_IDEA}]},
        full_permissions=True,
    )

    assert result.materialized is True
    assert result.strategy is not None
    assert result.strategy["id"] == 1
    assert Path(str(result.strategy["active_file_path"])).exists()
    assert result.blueprint_artifact_path is not None
    assert Path(result.blueprint_artifact_path).exists()
    assert result.metadata_artifact_path is not None
    assert Path(result.metadata_artifact_path).exists()


def test_strategy_creator_asks_for_missing_inputs_before_generation(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Create a mean reversion strategy.",
        full_permissions=True,
    )

    assert result.needs_clarification is True
    assert result.blueprint is None
    assert result.rendered_code == ""
    assert result.materialized is False
    assert "instrument_or_market" in result.missing_inputs
    assert "timeframe" in result.missing_inputs
    assert "risk_rule" in result.missing_inputs
    assert result.clarification_question is not None


def test_strategy_creator_preserves_explicit_rsi_cross_rules_and_fixed_lot_sizing(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    idea = """
Create an RSI strategy for EURUSD.
- timeframe
  H1
- entry_rule
buy when crosses up 50 on RSI (12)
sell when crosses down 50 on RSI (12)
- exit_rule
Exit buy when crosses down 50 on RSI (12)
Exit sell when crosses up 50 on RSI (12)
- risk_rule
No sl or tp exit points are already defined in exit logic
- position_sizing
fixed 0.1 lots
Risk management: 'ignore_stop_loss_take_profit': True
"""

    result = agent.create_from_idea(
        user_id=1,
        idea=idea,
        full_permissions=False,
    )

    assert result.needs_confirmation is True
    interpretation = result.final_interpretation
    assert interpretation is not None
    assert interpretation["assets"] == ["EURUSD"]
    assert interpretation["timeframe"] == "H1"
    assert interpretation["entry_logic"] == [
        "Enter LONG when RSI(12) crosses up through 50 on the completed bar.",
        "Enter SHORT when RSI(12) crosses down through 50 on the completed bar.",
    ]
    assert interpretation["exit_logic"] == [
        "Exit LONG when RSI(12) crosses down through 50 on the completed bar.",
        "Exit SHORT when RSI(12) crosses up through 50 on the completed bar.",
    ]
    assert interpretation["risk_management"]["stop_loss"] is None
    assert interpretation["risk_management"]["take_profit"] is None
    assert interpretation["risk_management"]["ignore_stop_loss_take_profit"] is True
    assert interpretation["position_sizing"]["sizing_rule"] == "Use fixed 0.1 lots per trade."


def test_strategy_creator_rejects_indicator_words_as_context_symbol(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Create an RSI strategy. H1. Buy when RSI crosses up 50. Exit when RSI crosses down 50. Fixed 0.1 lots. No SL or TP.",
        context={"symbol": "RSI", "timeframe": "H1"},
        full_permissions=False,
    )

    assert result.needs_clarification is True
    assert "instrument_or_market" in result.missing_inputs


def test_strategy_creator_uses_recent_confirmation_memory_for_create_above(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    confirmation = """CONFIRMATION:

Final interpretation:
- Strategy type: technical
- Assets: EURUSD
- Timeframe: H1

Entry logic:
- Enter LONG when RSI(12) crosses up through 50 on the completed bar.
- Enter SHORT when RSI(12) crosses down through 50 on the completed bar.

Exit logic:
- Exit LONG when RSI(12) crosses down through 50 on the completed bar.
- Exit SHORT when RSI(12) crosses up through 50 on the completed bar.

Risk management:
- {'stop_loss': None, 'take_profit': None, 'ignore_stop_loss_take_profit': True, 'additional_rules': ['No stop-loss or take-profit. Exits are governed by the explicit exit logic.']}

Position sizing:
- {'sizing_rule': 'Use fixed 0.1 lots per trade.', 'leverage': 1.0, 'allocation_notes': 'Fixed-lot position sizing supplied by the user.'}

Confirm or modify before I generate the strategy."""

    result = agent.create_from_idea(
        user_id=1,
        idea="You now have full permissions to create strategy above",
        context={
            "strategy_creator_recent_messages": [
                {"role": "assistant", "content": confirmation},
                {"role": "user", "content": "Confimed"},
                {"role": "user", "content": "proceed"},
                {"role": "user", "content": "Create"},
            ]
        },
        full_permissions=False,
    )

    assert result.needs_clarification is False
    assert result.needs_confirmation is False
    assert result.blueprint is not None
    assert result.blueprint.payload.asset_scope.assets == ["EURUSD"]
    assert result.blueprint.payload.risk_management.ignore_stop_loss_take_profit is True
    assert result.blueprint.payload.position_sizing.sizing_rule == "Use fixed 0.1 lots per trade."


def test_strategy_creator_accepts_common_confirmed_typo(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Confimed",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_RSI_IDEA}]},
        full_permissions=False,
    )

    assert result.needs_confirmation is False
    assert result.blueprint is not None


def test_strategy_creator_uses_llm_assist_inside_real_agent_for_fuzzy_rules(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    class FakeRuntime:
        provider_name = "fake"

        def _call_llm(self, system_prompt: str, user_prompt: str) -> dict[str, object]:
            assert "bounded LLM interpretation assist" in system_prompt
            return {
                "content": """
{
  "summary": "Interpreted RSI midline cross rules.",
  "candidate_patch": {
    "asset_scope": {"assets": ["EURUSD"], "timeframe": "H1", "data_granularity": "H1"},
    "entry_logic": [
      "Enter LONG when RSI(12) crosses up through 50 on the completed bar.",
      "Enter SHORT when RSI(12) crosses down through 50 on the completed bar."
    ],
    "exit_logic": [
      "Exit LONG when RSI(12) crosses down through 50 on the completed bar.",
      "Exit SHORT when RSI(12) crosses up through 50 on the completed bar."
    ],
    "risk_management": {
      "stop_loss": null,
      "take_profit": null,
      "ignore_stop_loss_take_profit": true,
      "additional_rules": ["No stop-loss or take-profit. Exits are governed by the explicit exit logic."]
    },
    "position_sizing": {
      "sizing_rule": "Use fixed 0.1 lots per trade.",
      "leverage": 1.0,
      "allocation_notes": "Fixed-lot position sizing supplied by the user."
    }
  },
  "missing_inputs": [],
  "confidence": 91
}
"""
            }

    with patch("backend.agents.strategy_creator_agent.create_llm_runtime", return_value=FakeRuntime()) as mock_runtime:
        result = agent.create_from_idea(
            user_id=1,
            idea="Create a EURUSD H1 RSI(12) midline cross strategy, no stops or targets, fixed 0.1 lots.",
            full_permissions=False,
        )

    assert mock_runtime.called is True
    assert result.needs_clarification is False
    assert result.needs_confirmation is True
    assert result.final_interpretation is not None
    assert result.final_interpretation["entry_logic"][0] == "Enter LONG when RSI(12) crosses up through 50 on the completed bar."
    assert result.final_interpretation["risk_management"]["ignore_stop_loss_take_profit"] is True


def test_strategy_creator_asks_permission_for_missing_indicator(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea=(
            "Create a SuperTrend strategy for EURUSD H1. Enter long when SuperTrend flips bullish, "
            "exit when SuperTrend flips bearish, use a 50 pip stop loss and 100 pip take profit, "
            "and risk 1% position size per trade."
        ),
        full_permissions=True,
    )

    assert result.needs_clarification is True
    assert "indicator_creation_permission" in result.missing_inputs
    assert result.materialized is False


def test_strategy_creator_creates_missing_indicator_with_permission(tmp_path: Path) -> None:
    agent = _agent(tmp_path)

    result = agent.create_from_idea(
        user_id=1,
        idea="Confirm and generate it.",
        context={"strategy_creator_recent_messages": [{"role": "user", "content": COMPLETE_SUPERTREND_IDEA}]},
        full_permissions=True,
    )

    indicator_path = tmp_path / "indicators" / "custom" / "supertrend.py"
    init_path = tmp_path / "indicators" / "custom" / "__init__.py"

    assert result.needs_clarification is False
    assert result.materialized is True
    assert result.indicator_artifacts
    assert result.indicator_artifacts[0]["materialized"] is True
    assert indicator_path.exists()
    assert "def supertrend" in indicator_path.read_text(encoding="utf-8")
    assert "from services.indicator.custom.supertrend import supertrend" in init_path.read_text(encoding="utf-8")
    assert result.artifact is not None
    assert result.artifact["indicator_dependencies"][0]["available"] is False
