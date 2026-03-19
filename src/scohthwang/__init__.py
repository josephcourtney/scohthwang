"""scohthwang — composable algorithms for bipartite correspondence finding.

Commonly-used symbols are re-exported here so callers can write::

    from scohthwang import hungarian_with_unmatched, needleman_wunsch_alignment

instead of importing from the individual sub-modules.  All sub-modules remain
importable directly for cases where finer-grained imports are preferred.
"""

from __future__ import annotations

__version__ = "0.1.0"

# models
# align
from scohthwang.align import (
    infer_offset_from_sequences,
    infer_seq_offset,
    needleman_wunsch_alignment,
)

# assign
from scohthwang.assign import hungarian_square, hungarian_with_unmatched

# block
from scohthwang.block import (
    BlockingFn,
    all_pairs,
    compose_blocks,
    key_equality_block,
    predicate_block,
)

# canonicalize
from scohthwang.canonicalize import (
    CanonicalizeRule,
    make_canonicalizer,
    normalize_str,
    sort_key_none_last,
)

# match
from scohthwang.match import (
    Level,
    group_and_match,
    hierarchical_match,
    match_within_group,
)
from scohthwang.models import (
    LARGE_COST,
    AlignedPair,
    CostMatrix,
    MatchResult,
    OffsetInferenceResult,
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

__all__ = [
    # models
    "LARGE_COST",
    "AlignedPair",
    # block
    "BlockingFn",
    # canonicalize
    "CanonicalizeRule",
    # score
    "ConstraintFn",
    "CostMatrix",
    # match
    "Level",
    "MatchResult",
    "OffsetInferenceResult",
    "PairCostConfig",
    "PairCostFn",
    "WeightedFieldCost",
    "all_pairs",
    "compose_blocks",
    "group_and_match",
    "hierarchical_match",
    # assign
    "hungarian_square",
    "hungarian_with_unmatched",
    # align
    "infer_offset_from_sequences",
    "infer_seq_offset",
    "key_equality_block",
    "make_canonicalizer",
    "make_nested_cost_fn",
    "make_pair_cost_fn",
    "match_within_group",
    "needleman_wunsch_alignment",
    "normalize_str",
    "predicate_block",
    "sort_key_none_last",
]
