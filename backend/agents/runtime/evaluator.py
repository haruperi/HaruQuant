"""Evaluator models and services for runtime trajectory assessment."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable

from haruquant.utils import logger

@dataclass(frozen=True)
class EvaluatorRubricCriterion:
    """One weighted evaluator rubric criterion."""

    name: str
    weight: float
    passing_score: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("criterion name must be non-empty")
        if self.weight <= 0:
            raise ValueError("criterion weight must be positive")
        if not 0 <= self.passing_score <= 1:
            raise ValueError("passing_score must be between 0 and 1")


@dataclass(frozen=True)
class EvaluatorRubric:
    """Named evaluator rubric for trajectory scoring."""

    rubric_name: str
    criteria: tuple[EvaluatorRubricCriterion, ...]

    def __post_init__(self) -> None:
        if not self.rubric_name:
            raise ValueError("rubric_name must be non-empty")
        if not self.criteria:
            raise ValueError("criteria must be non-empty")


@dataclass(frozen=True)
class TrajectoryEvaluation:
    """Score bundle for an evaluated trajectory run."""

    rubric_name: str
    rubric_scores: dict[str, float]
    overall_score: float
    verdict: str


@dataclass(frozen=True)
class ResearchAssertionCheck:
    """Unsupported-assertion detection result for research outputs."""

    supported: bool
    unsupported_claims: tuple[str, ...]


@dataclass(frozen=True)
class RefinementRecommendation:
    """Generated refinement guidance from evaluator findings."""

    improvement_actions: tuple[str, ...]
    focus_areas: tuple[str, ...]


class TrajectoryEvaluationService:
    """Weighted trajectory scoring over rubric criteria."""

    def evaluate(
        self,
        *,
        rubric: EvaluatorRubric,
        scores: dict[str, float],
    ) -> TrajectoryEvaluation:
        total_weight = sum(item.weight for item in rubric.criteria)
        weighted_score = 0.0
        verdict = "pass"
        for criterion in rubric.criteria:
            score = scores.get(criterion.name, 0.0)
            weighted_score += score * criterion.weight
            if score < criterion.passing_score:
                verdict = "warning" if verdict == "pass" else verdict
        overall_score = weighted_score / total_weight
        if overall_score < 0.5:
            verdict = "fail"
        return TrajectoryEvaluation(
            rubric_name=rubric.rubric_name,
            rubric_scores={key: scores.get(key, 0.0) for key in scores},
            overall_score=overall_score,
            verdict=verdict,
        )


def detect_unsupported_assertions(
    *,
    claims: Iterable[str],
    evidence_refs: Iterable[str],
) -> ResearchAssertionCheck:
    evidence = tuple(evidence_refs)
    unsupported = tuple(claim for claim in claims if not evidence and claim)
    return ResearchAssertionCheck(
        supported=not unsupported,
        unsupported_claims=unsupported,
    )


def generate_refinement_recommendations(
    *,
    evaluation: TrajectoryEvaluation,
    unsupported_assertions: ResearchAssertionCheck | None = None,
) -> RefinementRecommendation:
    actions: list[str] = []
    focus_areas: list[str] = []

    if evaluation.verdict != "pass":
        actions.append("Revise low-scoring sections before advancing workflow.")
        focus_areas.extend(
            criterion
            for criterion, score in evaluation.rubric_scores.items()
            if score < 0.7
        )

    if unsupported_assertions is not None and not unsupported_assertions.supported:
        actions.append("Add grounded evidence for unsupported claims.")
        focus_areas.append("grounding")

    return RefinementRecommendation(
        improvement_actions=tuple(dict.fromkeys(actions)),
        focus_areas=tuple(dict.fromkeys(focus_areas)),
    )


def hash_schema_name(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()
