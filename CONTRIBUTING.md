# Contributing to drozer-lite

Thanks for considering a contribution. drozer-lite is a Claude Code skill, not a Python package — there is no `pip install`, no test suite, no CI matrix. Contributions are content edits to four areas:

1. **Checklists** — new vulnerability patterns ported from real audit findings
2. **Vocabulary** — new canonical tags
3. **Detection keywords** — new profile triggers
4. **Fixtures** — vulnerable + clean Solidity pairs for smoke testing

## The one non-negotiable rule — No benchmark-specific names

**Every check, every keyword, every pattern description must be GENERIC.** Never embed audit-benchmark-specific identifiers (contract names, function names, variable names, token tickers from the protocol that motivated your fix) into any check, methodology section, red flags list, or example block.

Bad: *"Check if `confirmWithdrawal` has `whenWithdrawalNotPaused` — this is the Kinetiq GT-5 bug"*
Good: *"Check if a user-facing confirmation/settlement function has a local pause-flag modifier that's symmetric with the queue function's pause-flag modifier"*

Why: a check with a benchmark-specific function name like `confirmWithdrawal` will miss the exact same bug on any protocol that names it `finalizeClaim`, `settleRedemption`, or `completeExit`. The bug class is the same; the name is the accident. The skill must match the class, not the accident.

See `SKILL.md` → "Check Authorship Rules" (section CA-1 through CA-5) for the full rule and enforcement checklist. Every PR that touches `SKILL.md` or `checklists/*.md` must grep the diff for benchmark-specific identifiers before merge.

## Project philosophy

drozer-lite is intentionally narrow:

- **One LLM pass per audit, inside your existing Claude Code session.** Multi-agent orchestration belongs in the main [drozer](https://github.com/gdroz3r/drozer) pipeline.
- **Empirically curated.** Every check in a checklist must trace to a real audit finding that was missed before. No speculative patterns. The provenance is cited inside each check entry.
- **Developer-shaped.** Default output is canonical JSON. Markdown is opt-in.
- **Honest framing.** Every run ends with the disclaimer that drozer-lite catches pattern-level bugs only — never softens it.

Contributions that preserve these properties are welcome. Contributions that add multi-phase orchestration, benchmark-specific tuning, or speculative patterns will be redirected to the main drozer pipeline or rejected.

## 1. Adding a check to an existing checklist

Open the relevant `checklists/<profile>.md` file and add a new section in this exact format:

```markdown
### CHECK-NN: Title

**Provenance**: <source file in main drozer> → <benchmark project, e.g. "Virtuals H-05">
**Pattern**: <one to three sentences — what to look for in Solidity terms>
**Methodology**: <two to five sentences — how to investigate, what trace to follow, what state to compare>
**Red flags**:
- <concrete code construct>
- <concrete code construct>
- ...
```

Increment the check count in the file header. The check ID (e.g. `LEND-6`) follows the existing prefix in that file.

## 2. Adding a new profile

1. Create `checklists/<profile>.md` with the same Methodology preamble pattern as the existing files. Use a unique check ID prefix.
2. Port at least 3 real-finding-grounded checks from `Drozer-v2/skills/droz3r/analyses/` or your own audit history.
3. Add the profile name to the table in `SKILL.md` (Step 2 — Detect the protocol type) with case-insensitive trigger keywords. Pick keywords that appear at least 3 times in real code that uses this protocol type. Use `\b` boundaries where helpful.
4. Add the profile to `SKILL.md` Step 3 (Load the relevant checklists) so the skill knows it exists.
5. Add a vulnerable and clean fixture to `examples/fixtures/<profile>/{vulnerable,clean}.sol`.
6. Add a row to `examples/fixtures/expectations.json` pinning the profile, expected canonical `vulnerability_type`, and expected `affected_function`.
7. Open a PR with: rationale, source benchmark project the checks came from, fixture rationale.

## 3. Adding a vocabulary tag

Open `SKILL.md` and append a new entry to the **Canonical vulnerability vocabulary** section. Format:

```markdown
- `tag_name` — One-sentence description of the bug pattern. (SWC-NNN, CWE-NNN)
```

Include SWC and CWE references where applicable. Group by category (Reentrancy, Access control, Math, etc.).

## 4. Adding fixtures

`examples/fixtures/` holds small hand-crafted .sol files that serve as smoke tests for the skill. Each fixture pairs a vulnerable version with a clean version so users can verify both recall (finding real bugs) and precision (not flagging clean code).

Fixtures are the primary regression net. If you find that drozer-lite misses an obvious pattern, add a fixture for it first, then fix the check.

A fixture pair must:

- Be under 60 lines each (smoke tests, not production code)
- Demonstrate one canonical pattern from the loaded checklist
- Include the bug in a way the loaded checklist's Red flags can match
- Have a clean variant where the bug is remediated using the standard fix

## Manual validation after a checklist edit

Since drozer-lite is a skill (not a Python package), there is no automated test suite. After editing a check:

1. Open Claude Code.
2. Run `/drozer-lite examples/fixtures/<profile>/vulnerable.sol`.
3. Verify the new check fires AND the existing checks still fire.
4. Run `/drozer-lite examples/fixtures/<profile>/clean.sol`.
5. Verify NO finding matches the canonical type of the new check.
6. Repeat for any other profile your edit might affect.

If you broke something, fix it before committing.

## Commit and PR conventions

- Commits should be focused — one logical change per commit.
- PRs should describe: **what** changed, **why** it matters, and **how** it was manually validated.
- Reference the benchmark project or real finding that motivated the change.
- No benchmark-specific optimizations to the core methodology — `SKILL.md` stays generic.

## Reporting bugs in the skill itself

If the skill misbehaves (skips a check that should fire, fires on a clean fixture, breaks the JSON schema, refuses to disclose limitations), open an issue with:

- The exact `/drozer-lite ...` invocation
- The source file you ran it on
- The expected vs actual output
- The Claude Code version and model

Skill bugs are higher priority than missing checks — checks can be added incrementally, but the methodology must be sound.
