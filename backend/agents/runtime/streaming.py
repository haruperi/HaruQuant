"""Streaming LLM support for long-running tasks."""

from __future__ import annotations

from typing import Any, Callable, Protocol


class StreamChunkHandler(Protocol):
    """Protocol for handling streaming chunks."""
    def __call__(self, chunk: str) -> None: ...


def run_streaming(
    *,
    llm_runtime: Any,
    request: Any,
    context: Any,
    on_chunk: StreamChunkHandler | None = None,
) -> dict[str, Any]:
    """Run LLM with streaming response.

    Args:
        llm_runtime: The LLM runtime to use.
        request: The ADKRunRequest.
        context: The AgentExecutionContext.
        on_chunk: Optional callback for each text chunk.

    Returns:
        Dict with 'content' and 'final_state' keys.
    """
    try:
        import litellm
        messages = [{"role": "user", "content": str(request.input_payload)}]
        stream = litellm.completion(
            model=getattr(llm_runtime, "_model", "gemini-3.1-flash-lite-preview"),
            messages=messages,
            stream=True,
            temperature=getattr(llm_runtime, "_temperature", 0.1),
        )
        full_text = ""
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                full_text += delta
                if on_chunk:
                    on_chunk(delta)
        return {"content": full_text, "final_state": "COMPLETED"}
    except Exception as exc:
        return {"content": f"Error: {exc}", "final_state": "ERROR"}
