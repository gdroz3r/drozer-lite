"""Tests for vocab.py — canonicalization, synonyms, lookups."""

from __future__ import annotations

from drozer_lite.vocab import VOCABULARY, canonicalize, lookup


def test_vocabulary_has_at_least_30_entries() -> None:
    assert len(VOCABULARY) >= 30


def test_canonicalize_exact_match() -> None:
    canonical, mapped = canonicalize("reentrancy")
    assert canonical == "reentrancy"
    assert mapped is True


def test_canonicalize_case_insensitive() -> None:
    canonical, mapped = canonicalize("Reentrancy")
    assert canonical == "reentrancy"
    assert mapped is True


def test_canonicalize_synonym() -> None:
    canonical, mapped = canonicalize("CEI violation")
    assert canonical == "reentrancy"
    assert mapped is True


def test_canonicalize_unknown_returns_normalized() -> None:
    canonical, mapped = canonicalize("Some Brand New Bug Class")
    assert canonical == "some_brand_new_bug_class"
    assert mapped is False


def test_canonicalize_empty_string() -> None:
    canonical, mapped = canonicalize("")
    assert canonical == ""
    assert mapped is False


def test_lookup_returns_entry_with_swc() -> None:
    entry = lookup("reentrancy")
    assert entry is not None
    assert entry.swc_id == "SWC-107"
    assert entry.cwe_id == "CWE-841"


def test_lookup_unknown_returns_none() -> None:
    assert lookup("not_a_real_tag") is None


def test_synonym_uninitialized_proxy() -> None:
    canonical, mapped = canonicalize("missing _disableInitializers")
    assert canonical == "uninitialized_proxy"
    assert mapped is True


def test_synonym_share_inflation() -> None:
    canonical, mapped = canonicalize("first depositor attack")
    assert canonical == "share_inflation"
    assert mapped is True


def test_synonym_eip712_typehash() -> None:
    canonical, mapped = canonicalize("type hash mismatch")
    assert canonical == "eip712_typehash_mismatch"
    assert mapped is True


def test_all_vocabulary_entries_have_descriptions() -> None:
    for tag, entry in VOCABULARY.items():
        assert entry.tag == tag
        assert entry.description
