"""Anthropic API client wrapper.

Thin layer over the official `anthropic` SDK that enforces drozer-lite's
determinism contract:

- Temperature always 0
- Single message, no multi-turn
- Bounded retry (max 1 retry on transient error, no retry on schema error)
- Explicit timeout

Populated in Build Phase 3.
"""

from __future__ import annotations

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT_SECONDS = 180


def call_llm(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Make a single deterministic call to Anthropic and return the raw text.

    Temperature is locked to 0. The caller is responsible for parsing the
    response JSON and handling schema validation.
    """
    raise NotImplementedError("Build Phase 3")
