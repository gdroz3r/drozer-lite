"""Checklist loading and assembly.

Reads profile `.md` files from the `checklists/` directory and concatenates
the selected ones into a single prompt-ready string.

`universal.md` is always prepended. Profile names are validated against the
files actually present on disk, not against an in-memory list, so adding a
new profile is just a matter of dropping a new `.md` file into the directory.
"""

from __future__ import annotations

from pathlib import Path

CHECKLIST_DIR = Path(__file__).resolve().parent.parent / "checklists"

UNIVERSAL_PROFILE = "universal"


class ChecklistNotFoundError(FileNotFoundError):
    """Raised when a requested profile has no corresponding .md file."""


def available_profiles() -> list[str]:
    """List the profile names for which a checklist file exists on disk."""
    if not CHECKLIST_DIR.is_dir():
        return []
    return sorted(p.stem for p in CHECKLIST_DIR.glob("*.md"))


def load_checklist(profiles: list[str]) -> str:
    """Load and concatenate the requested profile checklists.

    `universal` is always prepended (deduplicated if the caller already
    included it). Order beyond universal is the order of the input list.

    Raises ChecklistNotFoundError if any requested profile has no file.
    """
    ordered: list[str] = [UNIVERSAL_PROFILE]
    for name in profiles:
        if name == UNIVERSAL_PROFILE:
            continue
        if name in ordered:
            continue
        ordered.append(name)

    chunks: list[str] = []
    for name in ordered:
        path = CHECKLIST_DIR / f"{name}.md"
        if not path.is_file():
            raise ChecklistNotFoundError(
                f"checklist file not found for profile {name!r}: {path}"
            )
        chunks.append(path.read_text(encoding="utf-8").rstrip())

    return "\n\n---\n\n".join(chunks) + "\n"
