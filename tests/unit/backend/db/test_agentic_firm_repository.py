from __future__ import annotations

from data.database import (
    AgenticFirmRepository,
    apply_pending_migrations,
    default_migrations_dir,
)


def test_agentic_firm_repository_persists_task_evidence_and_audit(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            """
            INSERT INTO core_workflows (
                workflow_id,
                workflow_type,
                environment,
                operating_mode,
                state,
                objective,
                scope_json,
                initiator_type,
                initiator_id,
                timeout_policy_json,
                stop_conditions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf-1",
                "strategy_creation",
                "paper",
                "MODE-002",
                "CREATED",
                "Create a strategy",
                "{}",
                "user",
                "operator",
                "{}",
                "[]",
            ),
        )

    task = repository.create_agent_task(
        task_id="task-1",
        workflow_id="wf-1",
        title="Create spec",
        description="Create a structured strategy spec",
        owner_agent="strategy_creator",
        expected_output_contract="StrategySpec",
    )
    assert task.workflow_id == "wf-1"
    assert task.status == "pending"

    event = repository.append_agent_task_event(
        task_id="task-1",
        event_type="assigned",
        actor_type="agent",
        actor_id="planner",
        from_status="pending",
        to_status="assigned",
    )
    assert event.task_id == "task-1"
    assert event.to_status == "assigned"

    evidence = repository.create_evidence_ref(
        evidence_id="ev-1",
        evidence_type="research_report",
        workflow_id="wf-1",
        task_id="task-1",
        uri="memory/evidence/ev-1.json",
        content_hash="hash-1",
        source_agent="research",
    )
    assert evidence.source_agent == "research"

    audit = repository.append_audit_log(
        audit_id="audit-1",
        actor_name="planner",
        agent_name="planner",
        action_type="assign_task",
        input_hash="input-hash",
        output_hash="output-hash",
        parent_task_id="task-1",
        workflow_id="wf-1",
        evidence_refs_json='["ev-1"]',
    )
    assert audit.audit_id == "audit-1"
    assert audit.parent_task_id == "task-1"


def test_agentic_firm_repository_persists_phase4_artifacts(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)

    task = repository.create_agent_task(
        task_id="task-artifacts",
        title="Persist artifacts",
        description="Persist Phase 4 artifacts",
        owner_agent="planner",
    )
    assert task.task_id == "task-artifacts"

    tool_call = repository.create_tool_call(
        tool_call_id="tool-1",
        task_id="task-artifacts",
        requesting_agent="planner",
        tool_name="get_symbol_data",
        arguments_json='{"symbol":"EURUSD"}',
    )
    assert tool_call["tool_name"] == "get_symbol_data"

    observation = repository.create_observation(
        observation_id="obs-1",
        task_id="task-artifacts",
        agent_name="research",
        observation_type="market_context",
        summary="EURUSD is range-bound.",
        confidence=0.8,
    )
    assert observation["confidence"] == 0.8

    decision = repository.create_decision(
        decision_id="decision-1",
        task_id="task-artifacts",
        agent_name="strategy_reviewer",
        decision_type="approve",
        decision="approve",
        rationale="Spec is testable and bounded.",
        evidence_refs_json='["ev-1"]',
        requires_risk_governor=True,
    )
    assert decision["requires_risk_governor"] == 1

    report = repository.create_research_report(
        research_report_id="research-1",
        task_id="task-artifacts",
        research_question="What is the EURUSD H1 context?",
        report_json='{"summary":"range-bound"}',
        created_by_agent="research",
        confidence=0.7,
    )
    assert report["created_by_agent"] == "research"

    spec = repository.create_strategy_spec(
        strategy_spec_id="spec-1",
        task_id="task-artifacts",
        strategy_id="strategy-1",
        strategy_name="EURUSD H1 Mean Reversion",
        version="0.1.0",
        market="forex",
        symbol="EURUSD",
        timeframe="H1",
        spec_json='{"entry_logic":["lower band"]}',
        created_by_agent="strategy_creator",
    )
    assert spec["symbol"] == "EURUSD"

    review = repository.create_strategy_review(
        strategy_review_id="review-1",
        strategy_spec_id="spec-1",
        strategy_id="strategy-1",
        reviewer_agent="strategy_reviewer",
        verdict="approve",
        review_json='{"verdict":"approve"}',
    )
    assert review["verdict"] == "approve"

    backtest = repository.create_backtest_run_ref(
        backtest_run_ref_id="bt-1",
        strategy_id="strategy-1",
        strategy_spec_id="spec-1",
        result_ref="memory/backtests/bt-1.json",
        summary_json='{"profit_factor":1.4}',
    )
    assert backtest["result_ref"].endswith("bt-1.json")

    robustness = repository.create_robustness_run_ref(
        robustness_run_ref_id="robust-1",
        strategy_id="strategy-1",
        strategy_spec_id="spec-1",
        robustness_type="walk_forward",
        result_ref="memory/robustness/robust-1.json",
    )
    assert robustness["robustness_type"] == "walk_forward"

    risk_review = repository.create_risk_review_ref(
        risk_review_ref_id="risk-review-1",
        strategy_id="strategy-1",
        reviewer_agent="risk_reviewer",
        verdict="approve_with_limits",
        review_ref="memory/risk/risk-review-1.json",
    )
    assert risk_review["reviewer_agent"] == "risk_reviewer"

    paper_trade = repository.create_paper_trade_ref(
        paper_trade_ref_id="paper-1",
        strategy_id="strategy-1",
        execution_ref="paper/order-1",
    )
    assert paper_trade["execution_ref"] == "paper/order-1"

    live_trade = repository.create_live_trade_ref(
        live_trade_ref_id="live-1",
        strategy_id="strategy-1",
        broker_ref="mt5/order-1",
    )
    assert live_trade["broker_ref"] == "mt5/order-1"


def test_agentic_firm_repository_persists_strategy_lifecycle(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)

    version = repository.create_strategy_version(
        strategy_version_id="strategy-version-1",
        strategy_id="strategy-1",
        version="1.0.0",
        code_ref="strategies/strategy-1.py",
        code_hash="sha256:code",
        created_by_agent="codegen",
    )
    assert version["version"] == "1.0.0"

    lifecycle = repository.upsert_strategy_lifecycle(
        strategy_id="strategy-1",
        current_state="research",
        active_strategy_version_id="strategy-version-1",
    )
    assert lifecycle["current_state"] == "research"

    updated = repository.upsert_strategy_lifecycle(
        strategy_id="strategy-1",
        current_state="paper_trading",
        active_strategy_version_id="strategy-version-1",
    )
    assert updated["current_state"] == "paper_trading"

    history = repository.append_strategy_status_history(
        strategy_id="strategy-1",
        from_state="research",
        to_state="paper_trading",
        reason="Backtest and risk review passed.",
        actor_type="agent",
        actor_id="portfolio_manager",
    )
    assert history["to_state"] == "paper_trading"

    promotion = repository.create_strategy_promotion_request(
        promotion_request_id="promo-1",
        strategy_id="strategy-1",
        from_state="research",
        to_state="paper_trading",
        requested_by_agent="portfolio_manager",
        rationale="Evidence bundle passed gates.",
    )
    assert promotion["status"] == "pending"

    retirement = repository.create_strategy_retirement_record(
        retirement_id="retire-1",
        strategy_id="strategy-1",
        retired_from_state="paper_trading",
        reason="Strategy edge decayed.",
        retired_by_actor_type="agent",
        retired_by_actor_id="risk_reviewer",
    )
    assert retirement["reason"] == "Strategy edge decayed."
