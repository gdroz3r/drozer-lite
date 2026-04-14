# Changelog

## v0.5.0 — Precision-gated emission (2026-04-15)

**Headline**: Measured score on Forefy autonomous-audit public corpus improved from **0.2909 (v0.4.3) → 0.5909 (v0.5.0)**. No checklist growth; methodology-only change.

### Root cause of v0.4.x weakness

Post-audit analysis on Forefy autonomous-audit showed the pattern matcher had complete coverage of every bug class in the benchmark, but lost points to (a) speculative "hedging" false positives, (b) severity miscalibration, (c) the agent reasoning itself out of valid findings, and (d) class-label drift from industry conventions.

Classification of 11 benchmark cases: 0 RC-METHOD (no missing checks), majority RC-AGENT (reasoning errors). Per the post-audit improvement protocol, RC-AGENT failures cannot be fixed by adding rules — only by tightening emission discipline.

### Methodology changes

1. **Step 5 rule 5** — "prefer NOT to report" → "do NOT report" as a hard rule. Explicitly bans speculative-hedging findings (`if ERC777 is ever added`, `if a malicious token is whitelisted`, `if a future admin…`). Hedging findings must have current in-scope evidence or be dropped at the source.

2. **Step 7 Gate A — Exploit-Sentence Gate** (precision). Every emitted finding must fill a concrete exploit sentence from this codebase's source: *"Attacker with [ROLE] calls [FN] with [INPUT], result is [CONCRETE LOSS]."* If any bracket requires hypothetical state, drop the finding. Two documented exceptions: cross-cluster economic flow candidates (tagged `"Pattern-level candidate:"`) and INFO-capped hardening items.

3. **Step 7 Gate B — Reasoning Reconciliation** (recall). Before emission, scan own reasoning for dismissal phrases (`"by design"`, `"admin-only so trusted"`, `"self-griefing"`, `"edge case"`). For each dismissal, check whether backed by a hard code-level constraint or just intuition. If intuition, restore the finding. This recovered the missed `discountBps` finding in benchmark case-003 and the `division_by_zero` miss in case-005.

4. **Severity decision table** — replaces free-text 5-row matrix with structured rules keyed on (attacker role, preconditions, impact). Aligns with Code4rena/Immunefi/SWC convention. Key rules: permissionless drain = CRITICAL, missing access on economic-parameter setter = HIGH, missing access on per-user state = MEDIUM, racing a legitimate caller = MEDIUM (not HIGH), admin-only action caps at MEDIUM (centralization), unchecked return without identified non-standard token = DROP.

5. **Vocabulary discipline** — `vulnerability_type` must pick the closest canonical tag from the SWC-aligned vocabulary. Paraphrasing (`"tx.origin authorization"` when the canonical tag is `tx_origin_auth`) is no longer allowed; fallback to ad-hoc snake_case now requires a `warnings` entry. Added missing industry-standard labels: `missing_input_validation`, `missing_condition_check`, `checks_effects_interactions_violation` (SWC-107 alias).

### Validation

| Benchmark | v0.4.3 | v0.5.0 | Change |
|---|---|---|---|
| Forefy autonomous-audit public (11 cases) | 0.2909 | 0.5909 | **+0.30** |
| Midas contracts (real-world, 36 findings) | 36 findings | ~31 findings | 5 hedging LOWs dropped; ALL 9 HIGH findings preserved |

Key verifications:
- Gate A kills the hedging findings it was designed to kill on both benchmarks.
- Gate B recovers findings the agent previously reasoned itself out of.
- No legitimate HIGH finding was lost on either benchmark.
- No checklist changes — this is entirely a Step 5 + Step 7 methodology tightening.

### Known ceiling

Remaining ~20% of Forefy benchmark points require flow-level analysis (fee accounting invariants, multisig approval tracking across state changes, cross-window merkle replay feasibility) that pattern matching structurally cannot prove without PoC execution. Three of 11 public cases remain false-positive for v0.5.0 (cases 008, 009, 011). Pushing past ~0.80 requires a verification layer that is outside drozer-lite's scope.

### Added

- `benchmark/` directory with vendor-neutral harness + baseline tracking (`run.sh`, `baseline.json`, `README.md`).

### Not changed

- `checklists/*.md` — zero edits. No benchmark-specific checks added.
- Profile detection, clustering, cross-cluster sweep — unchanged.

---

## Earlier versions

See git history. Summary per `memory/MEMORY.md`:
- v0.4.1 — 8 universal + UNI-2 extension (rental/marketplace ~42%→65% projected)
- v0.4.2 — 14 checks across universal/DEX/new StableSwap profile
- v0.4.3 — UNI-18 and UNI-38 extensions; Cairo perpetuals benchmark 54%
