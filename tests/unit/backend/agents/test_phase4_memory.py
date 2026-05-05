"""Tests for Phase 4: Long-Term Memory."""

from __future__ import annotations

import os
import tempfile

import pytest

from backend_retiring.agents.memory.model import SemanticMemory, EpisodicMemory, ProceduralMemory
from backend_retiring.agents.memory.rules import MemoryWriteRules


# ──────────────────────────────────────────────────────────────
# Memory Model Tests
# ──────────────────────────────────────────────────────────────

def test_semantic_memory_creation() -> None:
    """SemanticMemory should be created with required fields."""
    mem = SemanticMemory(
        memory_id="mem_001",
        content="EURUSD tends to trend during London session",
        category="market",
        importance=0.8,
    )
    assert mem.memory_id == "mem_001"
    assert mem.category == "market"
    assert mem.importance == 0.8
    assert mem.access_count == 0


def test_episodic_memory_creation() -> None:
    """EpisodicMemory should capture decision and outcome."""
    mem = EpisodicMemory(
        memory_id="ep_001",
        workflow_id="wf-001",
        agent_name="strategy_agent",
        goal="Generate EURUSD trade hypothesis",
        decision="Buy EURUSD at 1.0850",
        outcome="success",
        lesson="Trend continuation strategy works in low volatility",
    )
    assert mem.outcome == "success"
    assert mem.lesson is not None


def test_procedural_memory_creation() -> None:
    """ProceduralMemory should capture learned patterns."""
    mem = ProceduralMemory(
        memory_id="pm_001",
        pattern_name="trend_following_setup",
        description="Standard trend following workflow",
        steps=["research", "strategy", "compliance"],
        success_rate=0.85,
        usage_count=10,
    )
    assert len(mem.steps) == 3
    assert mem.success_rate == 0.85


# ──────────────────────────────────────────────────────────────
# Semantic Memory Store Tests
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def semantic_store():
    import uuid
    from backend_retiring.retrieval.embeddings import EmbeddingService
    from backend_retiring.agents.memory.semantic import SemanticMemoryStore
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    return SemanticMemoryStore(
        embeddings=embeddings,
        persist_dir=None,
        collection_name=f"test_semantic_{uuid.uuid4().hex[:8]}",
    )


def test_semantic_store_and_retrieve(semantic_store) -> None:
    """Should store and retrieve memories by semantic similarity."""
    semantic_store.store("EURUSD tends to rise during European trading hours", "market", importance=0.8)
    semantic_store.store("GBPJPY is volatile during London-Tokyo overlap", "market", importance=0.7)

    results = semantic_store.retrieve("European forex trading", top_k=2)
    assert len(results) >= 1
    assert results[0].category == "market"


def test_semantic_store_filter_by_category(semantic_store) -> None:
    """Should filter memories by category."""
    semantic_store.store("EURUSD market fact", "market", importance=0.8)
    semantic_store.store("Risk limit rule", "risk", importance=0.8)

    results = semantic_store.retrieve("trading", top_k=5, category="market")
    for r in results:
        assert r.category == "market"


# ──────────────────────────────────────────────────────────────
# Episodic Memory Store Tests
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def episodic_store():
    from backend_retiring.agents.memory.episodic import EpisodicMemoryStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "episodic.db")
        yield EpisodicMemoryStore(db_path=db_path)


def test_episodic_record_and_search(episodic_store) -> None:
    """Should record and search episodic memories."""
    episodic_store.record(
        workflow_id="wf-001",
        agent_name="strategy_agent",
        goal="Generate trade hypothesis",
        decision="Buy EURUSD",
        outcome="success",
        lesson="Trend strategy works",
    )

    memories = episodic_store.search(agent_name="strategy_agent")
    assert len(memories) == 1
    assert memories[0].outcome == "success"


def test_episodic_get_lessons(episodic_store) -> None:
    """Should retrieve lessons from past failures."""
    episodic_store.record(
        workflow_id="wf-002",
        agent_name="risk_agent",
        goal="Assess risk",
        decision="Reject trade",
        outcome="failure",
        lesson="High volatility requires wider stops",
    )

    lessons = episodic_store.get_lessons(outcome_filter="failure")
    assert len(lessons) == 1
    assert "volatility" in lessons[0]


# ──────────────────────────────────────────────────────────────
# Procedural Memory Store Tests
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def procedural_store():
    from backend_retiring.agents.memory.procedural import ProceduralMemoryStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "procedural.db")
        yield ProceduralMemoryStore(db_path=db_path)


def test_procedural_store_record_and_usage(procedural_store) -> None:
    """Should record patterns and track usage."""
    memory_id = procedural_store.store(
        pattern_name="trend_following",
        description="Standard trend following workflow",
        steps=["research", "strategy", "compliance"],
    )

    # Record successful usages
    for _ in range(5):
        procedural_store.record_usage(memory_id, success=True)

    patterns = procedural_store.get_patterns(min_usage=3, min_success_rate=0.5)
    assert len(patterns) == 1
    assert patterns[0].success_rate == 1.0  # All successes


# ──────────────────────────────────────────────────────────────
# Memory Write Rules Tests
# ──────────────────────────────────────────────────────────────

def test_write_rules_semantic_importance() -> None:
    """High importance content should be remembered."""
    assert MemoryWriteRules.should_remember_semantic("Important market fact with detail", 0.8) is True
    assert MemoryWriteRules.should_remember_semantic("Trivial", 0.3) is False
    assert MemoryWriteRules.should_remember_semantic("", 0.9) is False  # Too short


def test_write_rules_episodic_outcome() -> None:
    """Failures and successes with lessons should be remembered."""
    assert MemoryWriteRules.should_remember_episodic("failure", "Learned something important") is True
    assert MemoryWriteRules.should_remember_episodic("success", "Key insight gained") is True
    assert MemoryWriteRules.should_remember_episodic("partial", None) is False
    assert MemoryWriteRules.should_remember_episodic("failure", None) is False  # No lesson


def test_write_rules_procedural_threshold() -> None:
    """Patterns need sufficient usage and success rate."""
    assert MemoryWriteRules.should_remember_procedural(0.8, 10) is True
    assert MemoryWriteRules.should_remember_procedural(0.4, 10) is False  # Low success rate
    assert MemoryWriteRules.should_remember_procedural(0.8, 1) is False  # Too few uses


def test_write_rules_compute_importance() -> None:
    """Importance should reflect outcome, evidence, and recurrence."""
    imp = MemoryWriteRules.compute_importance("failure", has_evidence=True, is_recurring=True)
    assert imp > 0.7  # Failure + evidence + recurring = high importance

    imp_low = MemoryWriteRules.compute_importance("success", has_evidence=False, is_recurring=False)
    assert imp_low < imp  # Simple success is less important
