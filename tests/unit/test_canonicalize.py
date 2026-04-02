"""Unit tests for scohthwang.canonicalize."""

from __future__ import annotations

import dataclasses

import pytest

from scohthwang.canonicalize import (
    CanonicalizeRule,
    make_canonicalizer,
    normalize_str,
    sort_key_none_last,
)

# ---------------------------------------------------------------------------
# Fixtures: minimal dataclasses used across tests
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Record:
    name: str | None
    auth_name: str | None
    code: str | None
    auth_code: str | None
    backup_code: str | None = None


@dataclasses.dataclass(frozen=True)
class NumRecord:
    seq_id: int | None
    auth_seq_id: int | None


# ---------------------------------------------------------------------------
# CanonicalizeRule
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_canonicalize_rule_is_frozen() -> None:
    rule = CanonicalizeRule("name", ["auth_name"])
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        rule.field_name = "other"  # type: ignore[misc]  # intentional mutation attempt to verify frozen rule semantics.


@pytest.mark.unit
@pytest.mark.small
def test_canonicalize_rule_stores_fields() -> None:
    rule = CanonicalizeRule("name", ["auth_name", "backup"])
    assert rule.field_name == "name"
    assert rule.fallback_chain == ["auth_name", "backup"]


# ---------------------------------------------------------------------------
# make_canonicalizer — basic fill behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_fill_none_primary_from_first_fallback() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name=None, auth_name="ALA", code="X", auth_code="Y")
    out = fn(r)
    assert out.name == "ALA"


@pytest.mark.unit
@pytest.mark.small
def test_nonnone_primary_is_not_overwritten() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name="GLY", auth_name="ALA", code="X", auth_code="Y")
    out = fn(r)
    assert out.name == "GLY"


@pytest.mark.unit
@pytest.mark.small
def test_skips_none_fallbacks_and_uses_first_nonnone() -> None:
    fn = make_canonicalizer([CanonicalizeRule("code", ["auth_code", "backup_code"])])
    r = Record(name="A", auth_name="A", code=None, auth_code=None, backup_code="Z")
    out = fn(r)
    assert out.code == "Z"


@pytest.mark.unit
@pytest.mark.small
def test_no_update_when_all_fallbacks_are_none() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name=None, auth_name=None, code="X", auth_code="Y")
    out = fn(r)
    assert out.name is None


@pytest.mark.unit
@pytest.mark.small
def test_multiple_rules_applied_independently() -> None:
    fn = make_canonicalizer([
        CanonicalizeRule("name", ["auth_name"]),
        CanonicalizeRule("code", ["auth_code"]),
    ])
    r = Record(name=None, auth_name="GLY", code=None, auth_code="GG")
    out = fn(r)
    assert out.name == "GLY"
    assert out.code == "GG"


@pytest.mark.unit
@pytest.mark.small
def test_numeric_field_filled_from_fallback() -> None:
    fn = make_canonicalizer([CanonicalizeRule("seq_id", ["auth_seq_id"])])
    r = NumRecord(seq_id=None, auth_seq_id=42)
    out = fn(r)
    assert out.seq_id == 42


@pytest.mark.unit
@pytest.mark.small
def test_numeric_field_not_overwritten() -> None:
    fn = make_canonicalizer([CanonicalizeRule("seq_id", ["auth_seq_id"])])
    r = NumRecord(seq_id=7, auth_seq_id=42)
    out = fn(r)
    assert out.seq_id == 7


@pytest.mark.unit
@pytest.mark.small
def test_missing_field_raises_value_error() -> None:
    fn = make_canonicalizer([CanonicalizeRule("missing", ["auth_name"])])
    r = Record(name=None, auth_name="ALA", code="X", auth_code="Y")
    with pytest.raises(ValueError, match="missing"):
        fn(r)


# ---------------------------------------------------------------------------
# make_canonicalizer — identity and allocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_returns_same_object_when_no_change() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name="GLY", auth_name="ALA", code="X", auth_code="Y")
    out = fn(r)
    assert out is r


@pytest.mark.unit
@pytest.mark.small
def test_empty_rules_returns_same_object() -> None:
    fn = make_canonicalizer([])
    r = Record(name="A", auth_name="B", code="C", auth_code="D")
    assert fn(r) is r


# ---------------------------------------------------------------------------
# make_canonicalizer — idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_idempotent_when_primary_filled() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name=None, auth_name="ALA", code="X", auth_code="Y")
    once = fn(r)
    twice = fn(once)
    assert once == twice


@pytest.mark.unit
@pytest.mark.small
def test_idempotent_when_nothing_to_fill() -> None:
    fn = make_canonicalizer([CanonicalizeRule("name", ["auth_name"])])
    r = Record(name="GLY", auth_name="ALA", code="X", auth_code="Y")
    assert fn(fn(r)) == fn(r)


@pytest.mark.unit
@pytest.mark.small
def test_idempotent_multiple_rules() -> None:
    fn = make_canonicalizer([
        CanonicalizeRule("name", ["auth_name"]),
        CanonicalizeRule("code", ["auth_code"]),
    ])
    r = Record(name=None, auth_name="SER", code=None, auth_code="SS")
    once = fn(r)
    twice = fn(once)
    assert once == twice


# ---------------------------------------------------------------------------
# normalize_str
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_none_returns_none() -> None:
    assert normalize_str(None) is None


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_strip_default() -> None:
    assert normalize_str("  hello  ") == "hello"


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_strip_false() -> None:
    assert normalize_str("  hello  ", strip=False) == "  hello  "


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_lower() -> None:
    assert normalize_str("Hello World", lower=True) == "hello world"


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_lower_and_strip() -> None:
    assert normalize_str("  ALA  ", lower=True, strip=True) == "ala"


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_lower_false_strip_true() -> None:
    assert normalize_str("  ALA  ", lower=False, strip=True) == "ALA"


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_empty_string() -> None:
    assert normalize_str("") == ""


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_whitespace_only_strip() -> None:
    assert normalize_str("   ", strip=True) == ""


@pytest.mark.unit
@pytest.mark.small
def test_normalize_str_already_clean() -> None:
    assert normalize_str("clean") == "clean"


# ---------------------------------------------------------------------------
# sort_key_none_last
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_sorts_last() -> None:
    values = [3, None, 1, None, 2]
    result = sorted(values, key=sort_key_none_last)
    assert result == [1, 2, 3, None, None]


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_last_all_none() -> None:
    result = sorted([None, None, None], key=sort_key_none_last)
    assert result == [None, None, None]


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_last_no_none() -> None:
    result = sorted([3, 1, 2], key=sort_key_none_last)
    assert result == [1, 2, 3]


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_last_strings() -> None:
    result = sorted(["b", None, "a", None, "c"], key=sort_key_none_last)
    assert result == ["a", "b", "c", None, None]


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_last_single_none() -> None:
    result = sorted([None], key=sort_key_none_last)
    assert result == [None]


@pytest.mark.unit
@pytest.mark.small
def test_sort_key_none_last_returns_tuple() -> None:
    assert sort_key_none_last(5) == (0, 5)
    assert sort_key_none_last(None) == (1, None)
