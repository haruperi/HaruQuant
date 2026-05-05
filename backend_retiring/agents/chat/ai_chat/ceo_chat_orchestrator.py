"""Bridge AI chat turns into the Agentic Firm CEO control plane."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from uuid import uuid4

from backend_retiring.agents.agent_registry import AgentRegistry, get_default_agent_registry
from backend_retiring.agents.orchestrator import AgentControlPlaneOrchestrator, AgentControlPlaneResult
from backend_retiring.agents.task_manager import AgentTaskManager
from data.database.repositories.agentic_firm_repository import AgenticFirmRepository
from backend_retiring.agents.chat.ai_chat.conversation_service import ConversationService
from backend_retiring.agents.chat.ai_chat.models import ConversationMessageRecord, ConversationThreadRecord


CHAT_ATTACHMENT_TO_FIRM_HINT: dict[str, dict[str, str]] = {
    "strategy_creator": {"preferred_intent": "strategy_creation", "preferred_department": "strategy_creator"},
    "strategy_refiner": {"preferred_intent": "strategy_creation", "preferred_department": "strategy_reviewer"},
    "backtest_analyst": {"preferred_intent": "backtest_diagnosis", "preferred_department": "backtest"},
    "risk_reviewer": {"preferred_intent": "risk_review", "preferred_department": "risk_reviewer"},
    "signal_proposal_builder": {"preferred_intent": "execution_proposal", "preferred_department": "execution"},
    "optimization_comparator": {"preferred_intent": "optimization_comparison", "preferred_department": "optimization"},
    "page_operator": {"preferred_intent": "page_action", "preferred_department": "ceo"},
    "haruquant_docs": {"preferred_intent": "research", "preferred_department": "research"},
}

LEGACY_CHAT_TOOL_TO_FIRM_TOOL: dict[str, str] = {
    "portfolio_summary": "get_account_snapshot",
    "open_positions": "get_open_positions",
    "backtest_summary": "get_backtest_result",
    "strategy_parameters": "get_strategy",
    "optimization_results": "get_analytics_summary",
    "risk_snapshot": "get_risk_snapshot",
    "symbol_stats": "get_symbol_data",
    "latest_candle": "get_latest_ohlcv",
    "internal_knowledge": "get_analytics_summary",
}

CHAT_SPECIALIST_TO_FIRM_DEPARTMENT: dict[str, str] = {
    "backtest_explainer_agent": "backtest",
    "portfolio_risk_agent": "risk_reviewer",
    "optimization_comparison_agent": "optimization",
    "knowledge_retrieval_agent": "research",
    "page_operator_agent": "ceo",
    "trading_advisor_agent": "ceo",
    "market_regime_agent": "market_intelligence",
    "strategy_code_review_agent": "strategy_reviewer",
    "final_responder_agent": "ceo",
}


@dataclass(frozen=True)
class CEOChatTurnResult:
    """Chat-compatible result from the Agentic Firm control plane."""

    text: str
    metadata: dict[str, Any]
    assistant_message: ConversationMessageRecord
    control_plane_result: AgentControlPlaneResult


class CEOChatOrchestrator:
    """Make the existing chatbot speak through the CEO Agent architecture."""

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        registry: AgentRegistry | None = None,
    ) -> None:
        self.conversation_service = conversation_service
        self.registry = registry or get_default_agent_registry()

    def handle_chat_turn(
        self,
        *,
        user_id: int,
        thread: ConversationThreadRecord,
        prompt: str,
        request_id: str,
        page_context: Any,
        conversation_state: Any,
        tool_context: dict[str, Any],
        attached_tool_ids: tuple[str, ...] = (),
        persist_user_message: bool = True,
        include_debug: bool = False,
    ) -> CEOChatTurnResult:
        started = time.perf_counter()
        operator_hints = self._operator_hints(attached_tool_ids)
        enriched_tool_context = {
            **tool_context,
            "attached_tool_ids": attached_tool_ids,
            "operator_hints": operator_hints,
            "chat_tools_are_hints_only": True,
        }
        workflow_id = f"firm-{request_id}"
        repository = AgenticFirmRepository(self.conversation_service.repository.db_path)
        control_plane = AgentControlPlaneOrchestrator(
            registry=self.registry,
            task_manager=AgentTaskManager(repository=repository),
        )
        firm_prompt = self._compose_firm_prompt(
            prompt=prompt,
            operator_hints=operator_hints,
            tool_context=enriched_tool_context,
        )
        result = control_plane.handle_user_request(
            user_request=firm_prompt,
            workflow_id=workflow_id,
            request_id=request_id,
        )
        text = self._format_ceo_text(result=result)
        latency_ms = int((time.perf_counter() - started) * 1000)

        if persist_user_message:
            self.conversation_service.add_message(
                user_id=user_id,
                thread_id=thread.thread_id,
                role="user",
                content=prompt,
                request_id=request_id,
                context_revision=page_context.payload.context_revision,
                metadata={
                    "agentic_firm_chat": True,
                    "operator_hints": operator_hints,
                },
            )

        metadata = self._metadata(
            request_id=request_id,
            thread_id=thread.thread_id,
            page_context=page_context,
            conversation_state=conversation_state,
            result=result,
            operator_hints=operator_hints,
            attached_tool_ids=attached_tool_ids,
            latency_ms=latency_ms,
        )
        assistant = self.conversation_service.add_message(
            user_id=user_id,
            thread_id=thread.thread_id,
            role="assistant",
            content=text,
            request_id=request_id,
            context_revision=page_context.payload.context_revision,
            tool_calls=[],
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            cost=None,
            latency_ms=latency_ms,
            metadata=metadata,
        )
        if include_debug:
            metadata["debug"] = {
                "firm_prompt": firm_prompt,
                "conversation_state": conversation_state.model_dump(mode="json")
                if hasattr(conversation_state, "model_dump")
                else None,
                "control_plane_result": {
                    "workflow_id": result.workflow_id,
                    "parent_task_id": result.parent_task_id,
                    "child_task_ids": result.child_task_ids,
                    "planner_result": result.planner_result.model_dump(mode="json"),
                    "final_response": result.final_response,
                },
            }
        return CEOChatTurnResult(
            text=text,
            metadata=metadata,
            assistant_message=assistant,
            control_plane_result=result,
        )

    @staticmethod
    def _operator_hints(attached_tool_ids: tuple[str, ...]) -> list[dict[str, str]]:
        return [
            {"tool_id": tool_id, **CHAT_ATTACHMENT_TO_FIRM_HINT[tool_id]}
            for tool_id in attached_tool_ids
            if tool_id in CHAT_ATTACHMENT_TO_FIRM_HINT
        ]

    @staticmethod
    def _compose_firm_prompt(
        *,
        prompt: str,
        operator_hints: list[dict[str, str]],
        tool_context: dict[str, Any],
    ) -> str:
        if not operator_hints:
            return prompt
        hint_text = ", ".join(
            f"{hint['tool_id']}=>{hint['preferred_intent']}/{hint['preferred_department']}"
            for hint in operator_hints
        )
        symbol = tool_context.get("symbol")
        timeframe = tool_context.get("timeframe")
        context_bits = []
        if symbol:
            context_bits.append(f"symbol={symbol}")
        if timeframe:
            context_bits.append(f"timeframe={timeframe}")
        suffix = f" Operator hints from legacy chat tools: {hint_text}."
        if context_bits:
            suffix += f" Context: {', '.join(context_bits)}."
        return f"{prompt.strip()}{suffix}"

    @staticmethod
    def _format_ceo_text(*, result: AgentControlPlaneResult) -> str:
        memo = result.final_response.get("ceo_memo")
        if not isinstance(memo, dict):
            return str(result.final_response.get("summary") or "CEO Agent completed the firm workflow.")
        primary_text = str(
            memo.get("recommendation")
            or memo.get("summary")
            or memo.get("answer")
            or memo.get("question")
            or memo.get("reason")
            or result.final_response.get("summary")
        )
        lines = [primary_text]
        responsibilities = memo.get("responsibilities")
        if isinstance(responsibilities, list) and responsibilities:
            lines.extend(["", "Responsibilities:"])
            lines.extend(f"- {item}" for item in responsibilities)
        boundaries = memo.get("boundaries")
        if isinstance(boundaries, list) and boundaries:
            lines.extend(["", "Boundaries:"])
            lines.extend(f"- {item}" for item in boundaries)
        required = memo.get("required_before_trading")
        if isinstance(required, list) and required:
            lines.extend(["", "Required before trading:"])
            lines.extend(f"- {item}" for item in required)
        resume_requirement = memo.get("resume_requirement")
        if isinstance(resume_requirement, str) and resume_requirement:
            lines.extend(["", resume_requirement])
        if memo.get("approval_required"):
            lines.extend(["", "Board approval is required before this can proceed."])
        return "\n".join(lines).strip()

    @staticmethod
    def _metadata(
        *,
        request_id: str,
        thread_id: str,
        page_context: Any,
        conversation_state: Any,
        result: AgentControlPlaneResult,
        operator_hints: list[dict[str, str]],
        attached_tool_ids: tuple[str, ...],
        latency_ms: int,
    ) -> dict[str, Any]:
        plan = result.planner_result
        ceo_memo = result.final_response.get("ceo_memo")
        specialist_agents = list(
            dict.fromkeys(agent_result.agent_name for agent_result in result.agent_results)
        )
        specialist_artifacts = [
            {
                "agent_name": agent_result.agent_name,
                "summary": f"{agent_result.agent_name} completed with status {agent_result.status}.",
                "task_id": agent_result.task_id,
                "status": agent_result.status,
                "evidence_refs": list(agent_result.evidence_refs),
            }
            for agent_result in result.agent_results
        ]
        return {
            "request_id": request_id,
            "thread_id": thread_id,
            "agentic_firm_chat": True,
            "response_mode": "agentic_firm",
            "task_class": plan.task_class,
            "response_style": plan.response_style,
            "domain_focus": plan.domain_focus,
            "answer_mode": plan.answer_mode,
            "conversation_plan_id": plan.conversation_plan_id,
            "clarification_required": plan.needs_clarification,
            "planner": {
                "source": plan.planner_source,
                "confidence": plan.planner_confidence,
                "intent": plan.intent,
                "risk_level": plan.risk_level,
                "artifact_expected": plan.artifact_expected,
                "backend_tools_to_run": plan.backend_tools_to_run,
                "allowed_agents": plan.allowed_agents,
                "expected_outputs": plan.expected_outputs,
                "evidence_requirements": plan.evidence_requirements,
                "requires_board_approval": plan.requires_board_approval,
                "requires_risk_governor": plan.requires_risk_governor,
            },
            "model": None,
            "generation_source": "agentic_firm_ceo",
            "provider_name": None,
            "context_revision": page_context.payload.context_revision,
            "tools_used": list(plan.backend_tools_to_run),
            "tools_denied": [],
            "legacy_chat_tools_as_hints": list(attached_tool_ids),
            "operator_hints": operator_hints,
            "legacy_tool_mapping": LEGACY_CHAT_TOOL_TO_FIRM_TOOL,
            "chat_specialist_mapping": CHAT_SPECIALIST_TO_FIRM_DEPARTMENT,
            "active_topic": getattr(conversation_state, "active_topic", None),
            "specialist_agents_used": specialist_agents,
            "specialist_artifacts": specialist_artifacts,
            "attached_tools": [
                {
                    "tool_id": hint["tool_id"],
                    "mapped_intent": hint["preferred_intent"],
                    "mapped_department": hint["preferred_department"],
                    "authority": "operator_hint_only",
                }
                for hint in operator_hints
            ],
            "firm_workflow": {
                "workflow_id": result.workflow_id,
                "request_id": result.request_id,
                "parent_task_id": result.parent_task_id,
                "child_task_ids": list(result.child_task_ids),
                "audit_id": result.audit_id,
                "agent_results": [
                    {
                        "agent_name": agent_result.agent_name,
                        "task_id": agent_result.task_id,
                        "status": agent_result.status,
                        "evidence_refs": list(agent_result.evidence_refs),
                    }
                    for agent_result in result.agent_results
                ],
            },
            "ceo_memo": ceo_memo,
            "telemetry": {
                "latency_ms": latency_ms,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "cost_usd": None,
            },
            "cost_policy": {
                "request_budget_key": None,
                "estimated_cost_usd": 0.0,
                "budget_downgraded": False,
                "workflow_cost_usd": 0.0,
                "within_workflow_budget": True,
            },
        }


__all__ = [
    "CEOChatOrchestrator",
    "CEOChatTurnResult",
    "CHAT_ATTACHMENT_TO_FIRM_HINT",
    "CHAT_SPECIALIST_TO_FIRM_DEPARTMENT",
    "LEGACY_CHAT_TOOL_TO_FIRM_TOOL",
]
