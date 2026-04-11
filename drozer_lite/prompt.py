"""Single-shot prompt assembly.

Builds the system message and user message that drive a single deterministic
LLM pass. Pure and side-effect-free — easy to unit test.

Design:
- The SYSTEM message contains the task instructions, the loaded checklist,
  the JSON schema, and a few-shot example. This is the cacheable portion.
- The USER message contains the contract source files. This varies per call
  and is not cacheable.

Returns a `BuiltPrompt` carrying both messages so the LLM client can apply
prompt caching to the system block independently from the user block.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "native.json"

SYSTEM_PREAMBLE = """\
You are drozer-lite, a deterministic Solidity vulnerability scanner. You receive
a curated checklist of vulnerability patterns (each one derived from a real
audit finding) and one or more Solidity source files. You return a single JSON
object listing every vulnerability you find that matches a check.

CORE RULES:
1. Only report findings that match a check in the loaded checklist. Do not
   invent generic best-practice issues. The checklist IS the spec.
2. Every finding must reference a specific function and file. If you cannot
   point to a specific location, do not report it.
3. Severity is one of CRITICAL, HIGH, MEDIUM, LOW, INFO. Use the matrix:
   - CRITICAL: permissionless theft >$100k OR protocol-wide fund lock
   - HIGH:     theft with conditions OR significant fund lock
   - MEDIUM:   meaningful loss with setup requirements
   - LOW:      limited impact, hard to exploit, or pure griefing
   - INFO:     best practice, hardening, non-exploitable
4. Use the canonical vocabulary tags listed at the bottom of each check
   (snake_case, e.g. `reentrancy`, `missing_access_control`,
   `signature_replay`). If no vocabulary tag fits, fall back to a short
   snake_case description.
5. Confidence is HIGH/MEDIUM/LOW. HIGH means the code clearly matches the
   pattern. MEDIUM means the pattern is present but exploitability depends
   on context you cannot fully see. LOW means uncertain.
6. The `source_profile` field MUST identify which checklist profile caught
   the finding (universal, vault, lending, dex, etc.).
7. Return ONE JSON object only. No prose, no markdown fences. The object
   must validate against the schema below.
"""

OUTPUT_INSTRUCTIONS = """\
RESPONSE FORMAT:
Return a single JSON object that validates against this schema (and nothing
else — no markdown, no commentary):

{schema}

Required top-level fields: scanner ("drozer-lite"), version, findings.
The `findings` array may be empty if no vulnerabilities are present.
"""

FEW_SHOT = """\
EXAMPLE — for illustration only, do not echo this in your response:

Input source (Vault.sol):
    function withdraw(uint256 amount) external {
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
        balances[msg.sender] -= amount;
    }

Expected output:
{
  "scanner": "drozer-lite",
  "version": "0.1.0",
  "profiles_used": ["universal", "reentrancy"],
  "files_analyzed": ["Vault.sol"],
  "findings": [
    {
      "vulnerability_type": "reentrancy",
      "affected_function": "withdraw",
      "affected_file": "Vault.sol",
      "severity": "HIGH",
      "explanation": "External call via .call{value:} occurs before the balance is decremented, allowing a malicious receiver to re-enter and drain.",
      "line_hint": 2,
      "confidence": "HIGH",
      "source_profile": "reentrancy"
    }
  ],
  "stats": {"llm_calls": 1},
  "warnings": []
}
"""


@dataclass(frozen=True)
class BuiltPrompt:
    system: str
    user: str


def _load_schema_text() -> str:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return json.dumps(schema, indent=2)


def _format_files(files: list[tuple[str, str]]) -> str:
    blocks: list[str] = []
    for name, content in files:
        blocks.append(f"=== {name} ===\n{content.rstrip()}\n")
    return "\n".join(blocks)


def build_prompt(
    checklist: str,
    files: list[tuple[str, str]],
    *,
    profiles_used: list[str],
) -> BuiltPrompt:
    """Compose the system and user messages.

    The system message is stable across calls with the same checklist and
    therefore cacheable. The user message contains the per-invocation source
    files and the list of profiles selected for this run.
    """
    schema_text = _load_schema_text()

    system = "\n\n".join(
        [
            SYSTEM_PREAMBLE.strip(),
            "CHECKLIST (your full set of vulnerability patterns):",
            checklist.strip(),
            OUTPUT_INSTRUCTIONS.format(schema=schema_text).strip(),
            FEW_SHOT.strip(),
        ]
    )

    user_header = (
        f"PROFILES SELECTED FOR THIS RUN: {', '.join(profiles_used)}\n"
        f"FILES TO AUDIT ({len(files)}):\n"
    )
    user = user_header + "\n" + _format_files(files)

    return BuiltPrompt(system=system, user=user)
