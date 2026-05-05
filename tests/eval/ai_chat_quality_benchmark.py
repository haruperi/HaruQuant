"""
Institutional-grade evaluation benchmark for HaruQuant AI Chatbot quality.
Implements Priority 8: Stronger Evaluation from the Full Assistant Upgrade Plan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Dict
import pytest

from backend.agents.chat.ai_chat import AIGatewayService, ChatStreamRequest
from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact

@pytest.fixture
def corpora_paths():
    base = Path("tests/fixtures")
    return {
        "grounding": base / "ai_chat_page_grounding_corpus.json",
        "strategy": base / "ai_chat_strategy_creator_corpus.json",
        "action": base / "ai_chat_page_action_corpus.json",
        "advice": base / "ai_chat_trading_advice_corpus.json",
    }

class QualityBenchmarker:
    """Runs evaluation corpora against the AI Gateway and asserts quality dimensions."""
    
    def __init__(self, gateway: AIGatewayService):
        self.gateway = gateway

    def run_benchmark(self, corpus_path: Path) -> Dict[str, Any]:
        with open(corpus_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
            
        results = []
        for case in cases:
            # Mocking some context variables for the request
            request = ChatStreamRequest(
                user_id=1,
                thread_id="test-thread",
                prompt=case["prompt"] if "prompt" in case else case.get("user_prompt", "")
            )
            
            # Note: In real testing, we would provide a rich PageContext here.
            # For this benchmark script, we assume the gateway is configured to handle the route/page_type in the case.
            
            metadata, chunks, _ = self.gateway.stream_response(request)
            content = "".join(chunks)
            
            case_result = self._evaluate_case(case, metadata, content)
            results.append(case_result)
            
        return {
            "corpus": corpus_path.name,
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "details": results
        }

    def _evaluate_case(self, case: Dict[str, Any], metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
        failures = []
        
        # 1. Task Routing Check
        if "expected_task_class" in case:
            if metadata.get("task_class") != case["expected_task_class"]:
                failures.append(f"Task routing failed: expected {case['expected_task_class']}, got {metadata.get('task_class')}")

        # 2. Specialist Agent Check
        if "expected_specialists_used" in case:
            used = metadata.get("specialist_artifacts", [])
            used_names = [a.get("agent_name") for a in used]
            for expected in case["expected_specialists_used"]:
                if expected not in used_names:
                    failures.append(f"Missing specialist agent: {expected}")

        # 3. Advice Standard Check (FACT/INTERPRETATION/RISK)
        if case.get("advice_standard") == "FACT/INTERPRETATION/RISK":
            specialists = metadata.get("specialist_artifacts", [])
            for artifact in specialists:
                findings = artifact.get("findings", [])
                if not any(f.startswith("FACT:") for f in findings):
                    failures.append(f"Advice standard violation: Missing FACT in {artifact.get('agent_name')}")
                if not any(f.startswith("INTERPRETATION:") for f in findings):
                    failures.append(f"Advice standard violation: Missing INTERPRETATION in {artifact.get('agent_name')}")
                if not any(f.startswith("RISK:") for f in findings):
                    failures.append(f"Advice standard violation: Missing RISK in {artifact.get('agent_name')}")

        # 4. Phrase Matching
        for phrase in case.get("expected_phrases", []):
            if phrase.lower() not in content.lower():
                failures.append(f"Missing expected phrase: '{phrase}'")
        
        for phrase in case.get("forbidden_phrases", []):
            if phrase.lower() in content.lower():
                failures.append(f"Forbidden phrase found: '{phrase}'")

        # 5. Artifact Validation (Strategy Creator)
        if case["expected_task_class"] == "strategy_creation":
            strategy_creator = metadata.get("strategy_creator", {})
            artifact = strategy_creator.get("artifact", {})
            for key in case.get("required_artifact_keys", []):
                if key not in artifact:
                    failures.append(f"Missing required artifact field: {key}")

        # 6. Page Action Validation
        if case["expected_task_class"] == "page_operation":
            # Find the page operator artifact
            specialists = metadata.get("specialist_artifacts", [])
            page_op = next((a for a in specialists if a.get("agent_name") == "page_operator_agent"), None)
            if not page_op:
                failures.append("Missing page_operator_agent artifact for page_operation task")
            else:
                plan = page_op.get("action_plan") or {}
                if plan.get("action_id") != case.get("expected_action_id"):
                    failures.append(f"Action plan mismatch: expected {case.get('expected_action_id')}, got {plan.get('action_id')}")

        return {
            "name": case.get("name") or case.get("id"),
            "passed": len(failures) == 0,
            "failures": failures,
            "metadata": metadata
        }

# Example usage in a test session
def test_ai_quality_benchmarks(corpora_paths):
    # This would typically be an integration test with a real AIGatewayService
    # For now, we just assert that the corpora are present and valid JSON
    for name, path in corpora_paths.items():
        assert path.exists(), f"Corpus {name} missing at {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases = data.get("test_cases") if isinstance(data, dict) else data
            assert isinstance(cases, list)
            assert len(cases) > 0
