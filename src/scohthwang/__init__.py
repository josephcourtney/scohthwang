"""scohthwang — composable algorithms for bipartite correspondence finding.

Commonly-used symbols are re-exported here so callers can write::

    from scohthwang import hungarian_with_unmatched, needleman_wunsch_alignment

instead of importing from the individual sub-modules.  All sub-modules remain
importable directly for cases where finer-grained imports are preferred.
"""

from __future__ import annotations

# models
from scohthwang.models import (
    LARGE_COST,
    AlignedPair,
    CostMatrix,
    MatchResult,
    OffsetInferenceResult,
)

# assign
from scohthwang.assign import hungarian_square, hungarian_with_unmatched

# align
from scohthwang.align import (
    infer_offset_from_sequences,
    infer_seq_offset,
    needleman_wunsch_alignment,
)

# score
from scohthwang.score import (
    ConstraintFn,
    PairCostConfig,
    PairCostFn,
    WeightedFieldCost,
    make_nested_cost_fn,
    make_pair_cost_fn,
)

# block
from scohthwang.block import (
    BlockingFn,
    all_pairs,
    compose_blocks,
    key_equality_block,
    predicate_block,
)

# match
from scohthwang.match import (
    Level,
    group_and_match,
    hierarchical_match,
    match_within_group,
)

# canonicalize
from scohthwang.canonicalize import (
    CanonicalizeRule,
    make_canonicalizer,
    normalize_str,
    sort_key_none_last,
)

__all__ = [
    # models
    "LARGE_COST",
    "AlignedPair",
    "CostMatrix",
    "MatchResult",
    "OffsetInferenceResult",
    # assign
    "hungarian_square",
    "hungarian_with_unmatched",
    # align
    "infer_offset_from_sequences",
    "infer_seq_offset",
    "needleman_wunsch_alignment",
    # score
    "ConstraintFn",
    "PairCostConfig",
    "PairCostFn",
    "WeightedFieldCost",
    "make_nested_cost_fn",
    "make_pair_cost_fn",
    # block
    "BlockingFn",
    "all_pairs",
    "compose_blocks",
    "key_equality_block",
    "predicate_block",
    # match
    "Level",
    "group_and_match",
    "hierarchical_match",
    "match_within_group",
    # canonicalize
    "CanonicalizeRule",
    "make_canonicalizer",
    "normalize_str",
    "sort_key_none_last",
]
