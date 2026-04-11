"""Anthropic API client wrapper.

Thin layer over the official `anthropic` SDK that enforces drozer-lite's
determinism contract:

- Temperature always 0
- Single message, no multi-turn
- System prompt cached via prompt-caching (the checklist is huge and reused)
- Bounded retry: 1 retry on transient API errors (overloaded, 5xx, network)
- Explicit timeout
- ANTHROPIC_API_KEY required at call time

Importing this module does NOT instantiate a client. The client is created
lazily on first call so unit tests that monkeypatch `call_llm` never need
the SDK to be configured.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

DEFAULT_MODEL = "claude-opus-4-5"  # API model ID — public Anthropic identifier
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT_SECONDS = 180
RETRY_BACKOFF_SECONDS = 2.0


class LLMError(Exception):
    """Raised when the Anthropic call fails after retries."""


class LLMConfigError(LLMError):
    """Raised when the environment is missing required configuration."""


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    retries: int


def _get_client():
    """Lazy SDK import + client construction. Tests can avoid this entirely."""
    try:
        import anthropic  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise LLMConfigError(
            "the 'anthropic' package is required to call the LLM. "
            "install drozer-lite with `pip install drozer-lite` to pull it in."
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY is not set. Export it before running drozer-lite."
        )
    return anthropic.Anthropic(api_key=api_key)


def _is_transient_error(exc: Exception) -> bool:
    """Decide whether an API exception merits a single retry."""
    name = type(exc).__name__
    transient_names = {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
        "APIStatusError",  # broad — narrow further if needed
    }
    return name in transient_names


def call_llm(
    *,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> LLMResponse:
    """Single deterministic call to Anthropic.

    `system` is sent as a cacheable system block (prompt caching).
    `user` is sent as a single user message. Temperature is locked to 0.

    Returns LLMResponse with the raw text and basic usage metadata.
    Raises LLMError after one failed retry on transient errors, or
    immediately on non-transient errors (auth, schema, model not found).
    """
    client = _get_client()

    system_blocks = [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages = [{"role": "user", "content": user}]

    last_exc: Exception | None = None
    for attempt in range(2):  # 1 initial + 1 retry
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                timeout=timeout,
                system=system_blocks,
                messages=messages,
            )
            text = "".join(
                block.text for block in resp.content if getattr(block, "type", "") == "text"
            )
            usage = getattr(resp, "usage", None)
            return LLMResponse(
                text=text,
                model=getattr(resp, "model", model),
                input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
                cached_tokens=getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
                retries=attempt,
            )
        except Exception as exc:  # noqa: BLE001 — we re-raise as LLMError below
            last_exc = exc
            if attempt == 0 and _is_transient_error(exc):
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            break

    raise LLMError(f"Anthropic call failed: {type(last_exc).__name__}: {last_exc}") from last_exc
