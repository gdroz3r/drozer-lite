"""Vulnerability vocabulary — drozer-lite's native tag set.

Each native tag is a short snake_case identifier with optional SWC Registry
and CWE cross-references. The set is intentionally compact (~30 entries)
and grounded in the vulnerability classes that actually appear in the
ported checklists. It is NOT an exhaustive taxonomy of every possible
vuln class.

`canonicalize(raw)` maps free-form LLM output (e.g. "Reentrancy",
"CEI violation", "external call before state update") to the canonical
tag (`reentrancy`). Mapping is conservative — when no rule fires, the
input is returned unchanged so the audit pipeline can flag it as
unmapped rather than silently mislabel it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VocabEntry:
    tag: str
    description: str
    swc_id: str | None = None
    cwe_id: str | None = None


VOCABULARY: dict[str, VocabEntry] = {
    # Reentrancy / external call ordering
    "reentrancy": VocabEntry(
        tag="reentrancy",
        description="External call before state update; re-entrant caller drains balance.",
        swc_id="SWC-107",
        cwe_id="CWE-841",
    ),
    "cross_function_reentrancy": VocabEntry(
        tag="cross_function_reentrancy",
        description="State changed in one function is read inconsistently in another via callback.",
        swc_id="SWC-107",
        cwe_id="CWE-841",
    ),
    "callback_hook_reentrancy": VocabEntry(
        tag="callback_hook_reentrancy",
        description="ERC777/721/1155 receiver hook reenters the calling contract before state finalization.",
        swc_id="SWC-107",
        cwe_id="CWE-841",
    ),
    # Access control
    "missing_access_control": VocabEntry(
        tag="missing_access_control",
        description="State-changing function lacks an authorization check.",
        swc_id="SWC-105",
        cwe_id="CWE-284",
    ),
    "tx_origin_auth": VocabEntry(
        tag="tx_origin_auth",
        description="Authorization decision uses tx.origin instead of msg.sender.",
        swc_id="SWC-115",
        cwe_id="CWE-477",
    ),
    "privilege_retention_after_transfer": VocabEntry(
        tag="privilege_retention_after_transfer",
        description="Deployer or prior owner retains non-owner roles after ownership transfer.",
        swc_id="SWC-105",
        cwe_id="CWE-284",
    ),
    "rate_limit_bypass": VocabEntry(
        tag="rate_limit_bypass",
        description="Sibling function or alternative path bypasses an enforced rate limit.",
        cwe_id="CWE-799",
    ),
    # Math / arithmetic
    "integer_overflow": VocabEntry(
        tag="integer_overflow",
        description="Arithmetic overflow or underflow that wraps and corrupts state.",
        swc_id="SWC-101",
        cwe_id="CWE-190",
    ),
    "unsafe_cast_truncation": VocabEntry(
        tag="unsafe_cast_truncation",
        description="Narrowing cast (e.g. uint256 → uint160) truncates a critical value.",
        cwe_id="CWE-197",
    ),
    "decimal_scaling_mismatch": VocabEntry(
        tag="decimal_scaling_mismatch",
        description="Heterogeneous decimal scaling in accumulator math produces incorrect results.",
        cwe_id="CWE-682",
    ),
    "formula_parameter_transposition": VocabEntry(
        tag="formula_parameter_transposition",
        description="Formula parameters swapped (e.g. eloA/eloB) producing inverted results.",
        cwe_id="CWE-682",
    ),
    "division_by_zero": VocabEntry(
        tag="division_by_zero",
        description="Denominator can reach zero in a value-moving operation.",
        cwe_id="CWE-369",
    ),
    # Token / approval
    "unchecked_return_value": VocabEntry(
        tag="unchecked_return_value",
        description="External call return value (e.g. ERC20 transfer) is not verified.",
        swc_id="SWC-104",
        cwe_id="CWE-252",
    ),
    "non_standard_erc20": VocabEntry(
        tag="non_standard_erc20",
        description="Non-standard ERC20 token (e.g. USDT) returns no bool — call appears to succeed silently.",
        swc_id="SWC-104",
    ),
    "max_allowance_drain": VocabEntry(
        tag="max_allowance_drain",
        description="Approval to type(uint).max enables cross-contract drain by intermediate contract.",
        cwe_id="CWE-732",
    ),
    "low_level_call_silent_success": VocabEntry(
        tag="low_level_call_silent_success",
        description="Low-level call to non-existent address returns success without code-size guard.",
        swc_id="SWC-104",
        cwe_id="CWE-252",
    ),
    # Signatures
    "signature_replay": VocabEntry(
        tag="signature_replay",
        description="Signed message can be replayed across chains, contexts, or sessions.",
        swc_id="SWC-121",
        cwe_id="CWE-294",
    ),
    "permit_frontrun": VocabEntry(
        tag="permit_frontrun",
        description="Public permit() can be front-run to consume the user's signature without try/catch.",
        swc_id="SWC-121",
    ),
    "eip712_typehash_mismatch": VocabEntry(
        tag="eip712_typehash_mismatch",
        description="EIP-712 type hash differs from on-chain encoding; signatures never validate.",
        swc_id="SWC-121",
        cwe_id="CWE-345",
    ),
    "signature_authorization_gap": VocabEntry(
        tag="signature_authorization_gap",
        description="Signature is valid but the signer is not authorized for the target account.",
        cwe_id="CWE-863",
    ),
    "unchecked_signed_field": VocabEntry(
        tag="unchecked_signed_field",
        description="Signed struct field is included in the signature but never enforced on-chain.",
        cwe_id="CWE-345",
    ),
    # Oracles
    "oracle_staleness": VocabEntry(
        tag="oracle_staleness",
        description="Oracle data freshness is not validated before use.",
        cwe_id="CWE-665",
    ),
    "oracle_manipulation": VocabEntry(
        tag="oracle_manipulation",
        description="On-chain price source can be manipulated within a single transaction.",
        cwe_id="CWE-682",
    ),
    "oracle_failure_cascading": VocabEntry(
        tag="oracle_failure_cascading",
        description="Oracle failure (e.g. zero / max return) cascades into sell-at-zero or DoS.",
        cwe_id="CWE-754",
    ),
    # Vault / shares
    "share_inflation": VocabEntry(
        tag="share_inflation",
        description="ERC4626 share inflation via first-depositor rounding or donation attack.",
        cwe_id="CWE-682",
    ),
    "lifecycle_state_residue": VocabEntry(
        tag="lifecycle_state_residue",
        description="State remains active after lifecycle transition (e.g. closed market still ticks).",
        cwe_id="CWE-672",
    ),
    "missing_slippage_protection": VocabEntry(
        tag="missing_slippage_protection",
        description="Trade or LP function lacks min-out / deadline protection.",
        cwe_id="CWE-841",
    ),
    # Cross-chain
    "cross_chain_replay": VocabEntry(
        tag="cross_chain_replay",
        description="Cross-chain message can be replayed across chains or peers.",
        cwe_id="CWE-294",
    ),
    "missing_destination_check": VocabEntry(
        tag="missing_destination_check",
        description="Receiver does not verify it is the intended chain/destination of the payload.",
        cwe_id="CWE-345",
    ),
    "cross_chain_address_substitution": VocabEntry(
        tag="cross_chain_address_substitution",
        description="msg.sender is reused as a destination-chain identity (incompatible across chains).",
        cwe_id="CWE-840",
    ),
    "msgvalue_unsigned": VocabEntry(
        tag="msgvalue_unsigned",
        description="msg.value is not bound by the signature, allowing executor injection.",
        cwe_id="CWE-345",
    ),
    # Storage / proxy
    "uninitialized_proxy": VocabEntry(
        tag="uninitialized_proxy",
        description="Logic contract initializer is not disabled; can be initialized post-deploy.",
        swc_id="SWC-118",
        cwe_id="CWE-665",
    ),
    "storage_layout_collision": VocabEntry(
        tag="storage_layout_collision",
        description="Upgradeable contract storage layout changed without preserving slots.",
        swc_id="SWC-124",
        cwe_id="CWE-668",
    ),
    "uninitialized_storage": VocabEntry(
        tag="uninitialized_storage",
        description="Storage variable defaults to zero and an unset state passes guards.",
        swc_id="SWC-109",
        cwe_id="CWE-665",
    ),
    # Other
    "delegatecall_to_untrusted": VocabEntry(
        tag="delegatecall_to_untrusted",
        description="delegatecall target is attacker-controllable.",
        swc_id="SWC-112",
        cwe_id="CWE-829",
    ),
    "timestamp_dependence": VocabEntry(
        tag="timestamp_dependence",
        description="Critical logic depends on block.timestamp in a manipulable way.",
        swc_id="SWC-116",
        cwe_id="CWE-829",
    ),
    "missing_event_emission": VocabEntry(
        tag="missing_event_emission",
        description="State-changing operation does not emit a corresponding event.",
        cwe_id="CWE-778",
    ),
    "front_running": VocabEntry(
        tag="front_running",
        description="Same-block front-running enables ordering-dependent profit.",
        swc_id="SWC-114",
        cwe_id="CWE-362",
    ),
    "vrf_callback_gas": VocabEntry(
        tag="vrf_callback_gas",
        description="VRF fulfillment callback exceeds the configured gas limit and reverts.",
        cwe_id="CWE-400",
    ),
    "dust_order_dos": VocabEntry(
        tag="dust_order_dos",
        description="Residual-below-threshold orders block price levels and DoS the book.",
        cwe_id="CWE-400",
    ),
    "pause_time_accumulation": VocabEntry(
        tag="pause_time_accumulation",
        description="Time-dependent state continues to accumulate while the protocol is paused.",
        cwe_id="CWE-672",
    ),
}

# Synonym map: alternative phrasings the LLM might emit → canonical tag.
# Lowercased keys; matched after lowercasing the input.
_SYNONYMS: dict[str, str] = {
    "cei_violation": "reentrancy",
    "checks_effects_interactions_violation": "reentrancy",
    "external_call_before_state_update": "reentrancy",
    "reentrancy_attack": "reentrancy",
    "missing_authorization": "missing_access_control",
    "missing_auth": "missing_access_control",
    "missing_owner_check": "missing_access_control",
    "unauthorized_access": "missing_access_control",
    "tx_origin": "tx_origin_auth",
    "tx_origin_authentication": "tx_origin_auth",
    "tx_origin_used_for_auth": "tx_origin_auth",
    "uninitialized_logic": "uninitialized_proxy",
    "missing_disable_initializers": "uninitialized_proxy",
    "missing_disableinitializers": "uninitialized_proxy",
    "first_depositor_attack": "share_inflation",
    "donation_attack": "share_inflation",
    "share_inflation_attack": "share_inflation",
    "vault_inflation": "share_inflation",
    "stale_price": "oracle_staleness",
    "missing_staleness_check": "oracle_staleness",
    "missing_freshness_check": "oracle_staleness",
    "price_manipulation": "oracle_manipulation",
    "spot_price_manipulation": "oracle_manipulation",
    "missing_slippage": "missing_slippage_protection",
    "no_slippage_protection": "missing_slippage_protection",
    "missing_min_out": "missing_slippage_protection",
    "missing_deadline": "missing_slippage_protection",
    "type_hash_mismatch": "eip712_typehash_mismatch",
    "domain_separator_mismatch": "eip712_typehash_mismatch",
    "signature_replay_attack": "signature_replay",
    "cross_chain_signature_replay": "signature_replay",
    "permit_frontrunning": "permit_frontrun",
    "permit_griefing": "permit_frontrun",
    "missing_event": "missing_event_emission",
    "no_event_emitted": "missing_event_emission",
    "delegatecall_user_input": "delegatecall_to_untrusted",
    "arbitrary_delegatecall": "delegatecall_to_untrusted",
    "narrowing_cast": "unsafe_cast_truncation",
    "uint160_truncation": "unsafe_cast_truncation",
    "downcast": "unsafe_cast_truncation",
    "underflow": "integer_overflow",
    "overflow": "integer_overflow",
    "arithmetic_overflow": "integer_overflow",
    "div_by_zero": "division_by_zero",
    "divide_by_zero": "division_by_zero",
    "usdt_approve": "non_standard_erc20",
    "non_standard_token": "non_standard_erc20",
    "missing_return_check": "unchecked_return_value",
    "unchecked_call_return": "unchecked_return_value",
    "infinite_approval": "max_allowance_drain",
    "unlimited_approval": "max_allowance_drain",
    "missing_extcodesize": "low_level_call_silent_success",
    "call_to_eoa": "low_level_call_silent_success",
    "storage_collision": "storage_layout_collision",
    "proxy_storage_collision": "storage_layout_collision",
    "front_run": "front_running",
    "frontrun": "front_running",
    "frontrunning": "front_running",
    "stale_parameter": "pause_time_accumulation",
    "accumulation_during_pause": "pause_time_accumulation",
}


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def canonicalize(raw_type: str) -> tuple[str, bool]:
    """Map a free-form vulnerability type string to a canonical native tag.

    Returns (canonical_tag, was_mapped). If no rule fires, returns
    (normalized_input, False) — the caller can treat unmapped tags as
    advisory rather than discard them.
    """
    if not raw_type:
        return ("", False)
    norm = _normalize(raw_type)
    if norm in VOCABULARY:
        return (norm, True)
    if norm in _SYNONYMS:
        return (_SYNONYMS[norm], True)
    return (norm, False)


def lookup(tag: str) -> VocabEntry | None:
    """Return the VocabEntry for `tag` or None if not in the vocabulary."""
    return VOCABULARY.get(_normalize(tag))
