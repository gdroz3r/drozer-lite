"""Single-shot prompt assembly.

Builds the full LLM prompt: system instructions + checklist + vocabulary +
few-shot examples + contract source + output schema. Deterministic and
side-effect-free.

Populated in Build Phase 3.
"""

from __future__ import annotations


def build_prompt(
    checklist: str,
    files: list[tuple[str, str]],
    vocabulary: list[str],
    few_shot_examples: str,
    schema: str,
) -> str:
    """Compose the complete prompt string."""
    raise NotImplementedError("Build Phase 3")
