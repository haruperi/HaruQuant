"""Shared Research Department models and helpers."""

from .contracts import (
    CrossAssetContext,
    MacroContext,
    MarketContext,
    ResearchAgentArtifact,
    ResearchEvidenceRef,
    ResearchReportArtifact,
    ResearchRequestPayload,
    ResearchSourceRef,
    ResearchToStrategyHandoff,
    ResearchValidationResult,
    SeasonalityContext,
    SentimentContext,
    StrategyHypothesis,
    StrategyIdea,
    TechnicalContext,
)
from .permissions import RESEARCH_PERMISSION_PROFILE, RESEARCH_PERMISSION_PROFILE_NAME
from .scoring import ResearchScorecard, calculate_research_score
