"""Proposal pipeline services."""

from .transformer import ProposalTransformationConfig, transform_hypothesis_to_proposal

__all__ = [
    "ProposalTransformationConfig",
    "transform_hypothesis_to_proposal",
]
