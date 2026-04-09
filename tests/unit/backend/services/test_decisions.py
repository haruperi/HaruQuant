from __future__ import annotations

from backend.contracts.risk_assessment_decision.model import LimitConstraint
from backend.services.risk import compose_risk_decision
from backend.services.risk.restrictions import RestrictionEvaluation


def test_compose_risk_decision_approves_when_all_checks_pass():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
    )

    assert decision.decision == "APPROVE"
    assert decision.reasons == ("all_checks_passed",)


def test_compose_risk_decision_approves_with_limits_when_constraints_present():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
        limit_constraints=(
            LimitConstraint(constraint_type="max_size", value={"units": 1000}),
        ),
    )

    assert decision.decision == "APPROVE_WITH_LIMITS"
    assert decision.reasons == ("limits_required",)
    assert len(decision.limit_constraints) == 1


def test_compose_risk_decision_rejects_when_any_check_fails():
    decision = compose_risk_decision(
        checks=(
            RestrictionEvaluation(allowed=True),
            RestrictionEvaluation(allowed=False, reason_codes=("spread_threshold_exceeded",)),
        ),
    )

    assert decision.decision == "REJECT"
    assert decision.reasons == ("spread_threshold_exceeded",)


def test_compose_risk_decision_force_exit_takes_precedence():
    decision = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=False, reason_codes=("risk_limit_breach",)),),
        force_exit_symbols=("EURUSD",),
    )

    assert decision.decision == "FORCE_EXIT"
    assert decision.force_exit_symbols == ("EURUSD",)
    assert decision.reasons == ("force_exit_required",)
