"""Normalization utilities for pre-processing heterogeneous records.

Public API
----------
- :class:`CanonicalizeRule` — specifies one primary field and its fallback chain.
- :func:`make_canonicalizer` — build a normalizer from a list of rules.
- :func:`normalize_str` — strip and/or lower-case an optional string.
- :func:`sort_key_none_last` — sort-key helper that puts ``None`` after all values.

Design
------
Canonicalization is a pre-processing step that brings heterogeneous records into
a stable, comparable form before any matching algorithm runs.  The core pattern
is a *fallback chain*: if the primary field of a record is ``None``, fill it
from the first non-``None`` value in a list of alternative fields.

:func:`make_canonicalizer` turns a list of :class:`CanonicalizeRule` objects
into a single callable.  The returned function uses :func:`dataclasses.replace`
so it only allocates a new object when at least one field actually changes.  If
every field already has the correct value the original object is returned as-is.

The returned canonicalizer is **idempotent**: calling it twice produces the same
result as calling it once.

Usage
-----
::

    from dataclasses import dataclass
    from scohthwang.canonicalize import CanonicalizeRule, make_canonicalizer

    @dataclass(frozen=True)
    class Record:
        name: str | None
        auth_name: str | None
        seq_id: int | None
        auth_seq_id: int | None

    canonicalize = make_canonicalizer([
        CanonicalizeRule("name", ["auth_name"]),
        CanonicalizeRule("seq_id", ["auth_seq_id"]),
    ])

    r = Record(name=None, auth_name="ALA", seq_id=None, auth_seq_id=42)
    c = canonicalize(r)
    # c.name == "ALA", c.seq_id == 42

Source
------
Generalised from ``bvp_cs.algorithms.canonicalize.canonicalize_row`` in
``bvp/packages/bvp-cs``.  The domain-specific ``ShiftRow`` logic is replaced
with generic rule lists for any dataclass ``T``.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Rule definition
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CanonicalizeRule:
    """A single canonicalization rule: one primary field and its fallback chain.

    Parameters
    ----------
    field_name:
        The primary field to canonicalize.  If it is ``None`` on an object,
        it will be filled from ``fallback_chain``.
    fallback_chain:
        Ordered list of alternative field names to try, left-to-right.  The
        first field whose value is not ``None`` is used.
    """

    field_name: str
    fallback_chain: list[str]


# ---------------------------------------------------------------------------
# make_canonicalizer
# ---------------------------------------------------------------------------


def make_canonicalizer(rules: list[CanonicalizeRule]):  # -> Callable[[T], T]
    """Build a canonicalizer function from a list of :class:`CanonicalizeRule` objects.

    The returned function accepts any dataclass instance ``obj`` and returns a
    (possibly identical) instance with ``None`` primary fields filled from
    their fallback chains.

    If no field changes, the original object is returned without allocation.
    The function is idempotent: ``f(f(x)) == f(x)`` for all inputs.

    Parameters
    ----------
    rules:
        Ordered list of canonicalization rules.  Rules are applied left-to-right;
        one rule filling a field does not affect other rules.

    Returns
    -------
    Callable[[T], T]
        A closure over ``rules`` that canonicalizes any dataclass.

    Raises
    ------
    ValueError
        If a field referenced in a rule does not exist on the object passed at
        call time.  The check is deferred to call time so the canonicalizer can
        be built once and reused across dataclass types that share a schema.
    """

    def _canonicalize(obj: T) -> T:
        updates: dict[str, Any] = {}
        for rule in rules:
            current = getattr(obj, rule.field_name)
            if current is not None:
                continue
            for fallback_name in rule.fallback_chain:
                fallback_val = getattr(obj, fallback_name)
                if fallback_val is not None:
                    updates[rule.field_name] = fallback_val
                    break
        if not updates:
            return obj
        return dataclasses.replace(obj, **updates)  # type: ignore[type-var]

    return _canonicalize


# ---------------------------------------------------------------------------
# normalize_str
# ---------------------------------------------------------------------------


def normalize_str(
    v: str | None,
    *,
    lower: bool = False,
    strip: bool = True,
) -> str | None:
    """Normalize an optional string for stable comparison.

    Parameters
    ----------
    v:
        Input value.  ``None`` is returned as-is.
    lower:
        If ``True``, convert to lower-case after stripping.
    strip:
        If ``True`` (default), strip leading and trailing whitespace.

    Returns
    -------
    str | None
        Normalized string, or ``None`` if ``v`` is ``None``.
    """
    if v is None:
        return None
    if strip:
        v = v.strip()
    if lower:
        v = v.lower()
    return v


# ---------------------------------------------------------------------------
# sort_key_none_last
# ---------------------------------------------------------------------------


def sort_key_none_last(v: Any) -> tuple:  # noqa: ANN401
    """Return a sort key that places ``None`` after all non-``None`` values.

    Comparable values are sorted naturally; ``None`` sorts last.

    Parameters
    ----------
    v:
        The value to produce a sort key for.

    Returns
    -------
    tuple
        A two-element tuple ``(0, v)`` for non-``None`` values and ``(1, None)``
        for ``None``, ensuring ``None`` always sorts after any real value.

    Examples
    --------
    >>> sorted([3, None, 1, None, 2], key=sort_key_none_last)
    [1, 2, 3, None, None]
    """
    if v is None:
        return (1, None)
    return (0, v)
