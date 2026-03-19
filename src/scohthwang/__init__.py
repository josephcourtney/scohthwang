"""scohthwang — composable algorithms for bipartite correspondence finding.

Commonly-used symbols are re-exported here so callers can write::

    from scohthwang import hungarian_with_unmatched, needleman_wunsch_alignment

instead of importing from the individual sub-modules.  All sub-modules remain
importable directly for cases where finer-grained imports are preferred.
"""

from __future__ import annotations

__version__ = "0.2.0"

# models
# align
from scohthwang.align import (
    infer_best_offset_from_sequences_detailed,
    infer_offset_from_sequences,
    infer_offset_from_sequences_detailed,
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
    hierarchical_match_materialized,
    match_within_group,
    materialize_match_result,
)
from scohthwang.models import (
    LARGE_COST,
    AlignedPair,
    CostMatrix,
    MatchResult,
    MaterializedMatchResult,
    OffsetInferenceResult,
    OffsetScanCandidate,
    OffsetScanReport,
)

# score
from scohthwang.score import (
    CategoricalFieldCost,
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
    "CategoricalFieldCost",
    # score
    "ConstraintFn",
    "CostMatrix",
    # match
    "Level",
    "MatchResult",
    "MaterializedMatchResult",
    "OffsetInferenceResult",
    "OffsetScanCandidate",
    "OffsetScanReport",
    "PairCostConfig",
    "PairCostFn",
    "WeightedFieldCost",
    "all_pairs",
    "compose_blocks",
    "group_and_match",
    "hierarchical_match",
    "hierarchical_match_materialized",
    # assign
    "hungarian_square",
    "hungarian_with_unmatched",
    # align
    "infer_best_offset_from_sequences_detailed",
    "infer_offset_from_sequences",
    "infer_offset_from_sequences_detailed",
    "infer_seq_offset",
    "key_equality_block",
    "make_canonicalizer",
    "make_nested_cost_fn",
    "make_pair_cost_fn",
    "match_within_group",
    "materialize_match_result",
    "needleman_wunsch_alignment",
    "normalize_str",
    "predicate_block",
    "sort_key_none_last",
]
