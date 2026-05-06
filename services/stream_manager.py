"""Streaming transport utilities for AI Chat."""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import time
from typing import Any

import httpx


def _load_project_env_defaults() -> None:
    env_path = Path(__file__).resolve().parents[1] / "config" / "environments" / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env_defaults()


class StreamCancelled(RuntimeError):
    """Raised when the caller stops consuming a response stream."""


class ModelConfigurationError(RuntimeError):
    """Raised when model streaming is requested without runtime configuration."""


class ModelRuntimeError(RuntimeError):
    """Raised when a configured provider cannot complete a stream."""


class OpenAICompatibleStreamClient:
    """Provider-aware streaming client.

    The default model comes from HARUQUANT_AGENT_MODEL through config.agent_model.
    Provider selection follows the model name: Gemini models use GOOGLE_API_KEY,
    OpenAI/GPT models use OPENAI_API_KEY, and ollama/... models use the local
    Ollama server.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        provider_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("HARUQUANT_AI_GATEWAY_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key
        self.provider_name = provider_name or os.getenv("HARUQUANT_AI_GATEWAY_PROVIDER") or "model-config"
        self.timeout_seconds = timeout_seconds or float(os.getenv("HARUQUANT_AI_GATEWAY_TIMEOUT_SECONDS", "60"))

    @property
    def is_configured(self) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or self.api_key)

    def is_configured_for(self, *, model: str | None) -> bool:
        provider = self.provider_for_model(model or "")
        if provider == "google":
            return bool(self.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        if provider == "openai":
            return bool(self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("HARUQUANT_AI_GATEWAY_API_KEY"))
        if provider == "ollama":
            return True
        return False

    def provider_for_model(self, model: str) -> str:
        lowered = model.lower()
        if lowered.startswith("ollama/") or lowered.startswith("ollama:"):
            return "ollama"
        if lowered.startswith("openai/") or lowered.startswith("gpt-") or lowered.startswith(("o1", "o3", "o4")):
            return "openai"
        if lowered.startswith("gemini") or lowered.startswith("google/"):
            return "google"
        return "openai" if os.getenv("OPENAI_API_KEY") else "google"

    def provider_label_for_model(self, model: str) -> str:
        return {
            "google": "google-generative-ai",
            "openai": "openai",
            "ollama": "ollama",
        }.get(self.provider_for_model(model), self.provider_name)

    def stream_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        provider = self.provider_for_model(model)
        if provider == "ollama":
            yield from self._stream_ollama_chat(
                messages=messages,
                model=_strip_provider_prefix(model),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return
        if provider == "google":
            yield from self._stream_google_chat(
                messages=messages,
                model=_strip_provider_prefix(model),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return
        yield from self._stream_openai_chat(
            messages=messages,
            model=_strip_provider_prefix(model),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _stream_openai_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        api_key = self.api_key or os.getenv("HARUQUANT_AI_GATEWAY_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ModelConfigurationError("OPENAI_API_KEY is not configured for the selected model.")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line.removeprefix("data:").strip()
                    else:
                        data = line.strip()
                    if data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        (parsed.get("choices") or [{}])[0]
                        .get("delta", {})
                        .get("content")
                    )
                    if delta:
                        yield str(delta)

    def _stream_google_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        api_key = self.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ModelConfigurationError("GOOGLE_API_KEY is not configured for the selected model.")
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ModelConfigurationError("google-genai is not installed for Gemini streaming.") from exc

        system_instruction, contents = _google_contents_from_messages(messages)
        config: dict[str, Any] = {"temperature": temperature}
        if max_tokens:
            config["max_output_tokens"] = max_tokens
        if system_instruction:
            config["system_instruction"] = system_instruction

        try:
            client = genai.Client(api_key=api_key)
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                text = getattr(chunk, "text", None)
                if text:
                    yield str(text)
        except Exception as exc:  # pragma: no cover - provider SDK surface
            raise ModelRuntimeError(str(exc)) from exc

    def _stream_ollama_chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("HARUQUANT_OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                with client.stream("POST", f"{base_url.rstrip('/')}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            parsed = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        message = parsed.get("message")
                        if isinstance(message, dict):
                            content = message.get("content")
                            if content:
                                yield str(content)
                        if parsed.get("done"):
                            break
        except httpx.ConnectError as exc:
            raise ModelConfigurationError("Ollama is not reachable. Start Ollama or set OLLAMA_BASE_URL.") from exc
        except httpx.HTTPError as exc:
            raise ModelRuntimeError(str(exc)) from exc


class StreamManager:
    """Converts model and fallback text into UI stream events."""

    def text_tokens(self, text: str, *, chunk_size: int = 48, delay_seconds: float = 0.0) -> Iterator[str]:
        for index in range(0, len(text), chunk_size):
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            yield text[index : index + chunk_size]


__all__ = [
    "ModelConfigurationError",
    "ModelRuntimeError",
    "OpenAICompatibleStreamClient",
    "StreamCancelled",
    "StreamManager",
]


def _strip_provider_prefix(model: str) -> str:
    if model.startswith("openai/"):
        return model.removeprefix("openai/")
    if model.startswith("google/"):
        return model.removeprefix("google/")
    if model.startswith("ollama/"):
        return model.removeprefix("ollama/")
    if model.startswith("ollama:"):
        return model.removeprefix("ollama:")
    return model


def _google_contents_from_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": content}],
            }
        )
    return "\n\n".join(system_parts), contents or [{"role": "user", "parts": [{"text": ""}]}]
