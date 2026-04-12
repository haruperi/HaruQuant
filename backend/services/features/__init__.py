"""Feature pipeline package (IP-13/IP-14)."""

from .pipeline import FeaturePipeline, FeatureSpec
from .leakage import (
    TimeSplitResult,
    dump_masked_research_json,
    enforce_time_split,
    mask_research_artifact,
    validate_no_lookahead_features,
)

__all__ = [
    "FeaturePipeline",
    "FeatureSpec",
    "TimeSplitResult",
    "dump_masked_research_json",
    "enforce_time_split",
    "mask_research_artifact",
    "validate_no_lookahead_features",
]
