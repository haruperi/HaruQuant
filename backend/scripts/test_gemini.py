"""Quick LLM connection test via the internal agent runtime.

Usage:
    python backend/scripts/test_gemini.py

Checks:
  1. LLM provider registration (litellm, openai, google-adk)
  2. Model name resolution from HARUQUANT_AGENT_MODEL
  3. API key availability in environment
  4. Single-round LLM call with a trivial prompt
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

# Load .env file
_env_path = os.path.join(PROJECT_ROOT, "backend", "config", "environments", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.config.agent_model import AGENT_MODEL, MODEL_TIER, GENERATION_CONFIG
from backend.agents.runtime.llm_registry import get_provider
from backend.agents.runtime import create_llm_runtime, ADKRunRequest, ADKRunnerConfig, ADKRunnerService


def main() -> None:
    print("=" * 60)
    print("  Gemini / LLM Connection Test")
    print("=" * 60)
    print()

    # 1. Model config
    print(f"  HARUQUANT_AGENT_MODEL = {AGENT_MODEL}")
    print(f"  Model tier routing:  fast={MODEL_TIER['fast']}, standard={MODEL_TIER['standard']}")
    print(f"  Generation config:   {GENERATION_CONFIG}")
    print()

    # 2. API key check
    for key_name in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY"):
        val = os.environ.get(key_name, "")
        masked = f"{val[:6]}...{val[-4:]}" if len(val) > 10 else ("present" if val else "NOT SET")
        print(f"  {key_name} = {masked}")
    print()

    # 3. Provider resolution
    try:
        provider_cls = get_provider(model=AGENT_MODEL)
        print(f"  Resolved provider: {provider_cls.__name__}")
    except Exception as exc:
        print(f"  ❌ Provider resolution failed: {exc}")
        return
    print()

    # 4. Create runtime
    try:
        runtime = create_llm_runtime(model=AGENT_MODEL)
        print(f"  Runtime created:  {runtime.provider_name} / {runtime.model}")
    except Exception as exc:
        print(f"  ❌ Runtime creation failed: {exc}")
        return
    print()

    # 5. Test LLM call
    print("  Sending test prompt...")
    try:
        config = ADKRunnerConfig(runner_name="test_runner")
        runner = ADKRunnerService(config=config)

        request = ADKRunRequest(
            workflow_id="test",
            correlation_id="test-conn",
            agent_name="test",
            input_payload={
                "_system_prompt": "Answer with exactly the word OK and nothing else.",
                "question": "Is the connection working?",
            },
        )

        result = runner.run(agent=runtime, request=request)
        print(f"  ✅ LLM responded ({result.latency_ms}ms)")
        print(f"  Model:  {result.model}")
        print(f"  State:  {result.final_state}")

        payload = result.output_payload
        if isinstance(payload, dict):
            content = payload.get("content", payload.get("text", str(payload)))
        else:
            content = str(payload)

        print(f"  Output: {content[:200]}")

        # Token usage
        if result.token_usage:
            print(f"  Tokens:  input={result.token_usage.get('input_tokens', 'N/A')}, "
                  f"output={result.token_usage.get('output_tokens', 'N/A')}")

    except Exception as exc:
        print(f"  ❌ LLM call failed: {exc}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 60)
    print("  Connection test PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
