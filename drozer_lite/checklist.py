"""Checklist loading and assembly.

Reads profile `.md` files from the `checklists/` directory and concatenates
the selected ones into a single prompt-ready string.

Populated in Build Phase 2.
"""

from __future__ import annotations

from pathlib import Path

CHECKLIST_DIR = Path(__file__).resolve().parent.parent / "checklists"


def load_checklist(profiles: list[str]) -> str:
    """Load and concatenate the requested profile checklists.

    Always prepends `universal.md`. Returns a single Markdown string
    ready to drop into the LLM prompt.
    """
    raise NotImplementedError("Build Phase 2")
