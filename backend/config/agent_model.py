"""Centralized model configuration for all ADK agents.

Change AGENT_MODEL here to switch the LLM across the entire system.
Supports Gemini, OpenAI, local models (llama, ollama), etc.

Examples:
  AGENT_MODEL = "gemini-3.1-flash-lite-preview"  # Default
  AGENT_MODEL = "gemini-3.1-pro"                  # Higher quality
  AGENT_MODEL = "openai/gpt-4o"                   # OpenAI
  AGENT_MODEL = "ollama/llama3.1:70b"             # Local via Ollama
  AGENT_MODEL = "ollama/qwen2.5-coder:32b"        # Local coder model
"""

from __future__ import annotations

import os
from typing import Any, Dict

# ──────────────────────────────────────────────────────────────
# PRIMARY MODEL — change this ONE variable to switch all agents
# ──────────────────────────────────────────────────────────────
AGENT_MODEL = os.environ.get(
    "HARUQUANT_AGENT_MODEL",
    "gemini-3.1-flash-lite-preview",
)

# ──────────────────────────────────────────────────────────────
# MODEL TIER ROUTING — maps request complexity to model choice
# Used by cost governance to route simple requests to cheaper models
# ──────────────────────────────────────────────────────────────
MODEL_TIER = {
    "fast": os.environ.get(
        "HARUQUANT_FAST_MODEL",
        "gemini-3.1-flash-lite-preview",
    ),
    "standard": AGENT_MODEL,
    "premium": os.environ.get(
        "HARUQUANT_PREMIUM_MODEL",
        "gemini-3.1-pro",
    ),
    "fallback": os.environ.get(
        "HARUQUANT_FALLBACK_MODEL",
        "gemini-3.1-flash-lite-preview",
    ),
}

# ──────────────────────────────────────────────────────────────
# MODEL PARAMETERS — shared generation config
# ──────────────────────────────────────────────────────────────
GENERATION_CONFIG: Dict[str, Any] = {
    "temperature": float(os.environ.get("HARUQUANT_TEMPERATURE", "0.2")),
    "max_output_tokens": int(os.environ.get("HARUQUANT_MAX_TOKENS", "4096")),
    "top_p": float(os.environ.get("HARUQUANT_TOP_P", "0.95")),
    "top_k": int(os.environ.get("HARUQUANT_TOP_K", "40")),
}

# ──────────────────────────────────────────────────────────────
# COST LIMITS — per-request and per-workflow budgets (USD)
# ──────────────────────────────────────────────────────────────
COST_LIMITS = {
    "max_per_request_usd": float(
        os.environ.get("HARUQUANT_MAX_REQUEST_COST", "0.10")
    ),
    "max_per_workflow_usd": float(
        os.environ.get("HARUQUANT_MAX_WORKFLOW_COST", "0.50")
    ),
    "max_per_session_usd": float(
        os.environ.get("HARUQUANT_MAX_SESSION_COST", "2.00")
    ),
}


def get_model_for_tier(tier: str) -> str:
    """Return the model name for a given cost tier."""
    return MODEL_TIER.get(tier, AGENT_MODEL)


def get_all_model_names() -> list[str]:
    """Return all configured model names (for validation/metrics)."""
    return list(set(MODEL_TIER.values()) | {AGENT_MODEL})
