"""Operator strategy lifecycle routes."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services.utils.logger import logger
from backend.data.database import GovernanceRepository
from backend.data.database.sqlite.database_operations import DatabaseManager
from services.strategy.governance import (
    StrategyLifecycleState,
    StrategyLifecycleTransitionValidator,
)

router = APIRouter()
db_manager = DatabaseManager()
governance_repository = GovernanceRepository(db_manager.db_path)
transition_validator = StrategyLifecycleTransitionValidator()


class OperatorStrategyResponse(BaseModel):
    strategy_id: int
    user_id: int
    name: str
    status: str
    category: Optional[str] = None
    active_version: Optional[str] = None
    governance_strategy_id: str
    lifecycle_state: Optional[str] = None
    strategy_family: Optional[str] = None
    code_hash: Optional[str] = None
    parameter_hash: Optional[str] = None
    artifact_root: Optional[str] = None
    updated_at: str


class LifecycleUpdateRequest(BaseModel):
    lifecycle_state: StrategyLifecycleState


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_manager.db_path)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/strategies", response_model=List[OperatorStrategyResponse])
async def list_operator_strategies() -> List[OperatorStrategyResponse]:
    """List operational strategies with governance lifecycle metadata."""
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id AS strategy_id,
                    s.user_id,
                    s.name,
                    s.status,
                    s.category,
                    sv.version AS active_version,
                    COALESCE(s.governance_strategy_id, 'strategy:' || s.user_id || ':' || s.id)
                        AS governance_strategy_id,
                    s.strategy_family,
                    s.artifact_root,
                    s.updated_at,
                    g.current_lifecycle_state AS lifecycle_state,
                    g.code_hash,
                    g.parameter_hash,
                    g.strategy_family AS governance_strategy_family
                FROM strategies s
                LEFT JOIN strategy_versions sv ON s.active_version_id = sv.id
                LEFT JOIN gov_strategy_registry g
                    ON g.strategy_id = COALESCE(
                        s.governance_strategy_id,
                        'strategy:' || s.user_id || ':' || s.id
                    )
                ORDER BY s.updated_at DESC, s.id DESC
                """
            ).fetchall()

        return [
            OperatorStrategyResponse(
                **{
                    **dict(row),
                    "strategy_family": row["governance_strategy_family"]
                    or row["strategy_family"]
                    or row["category"]
                    or "custom",
                }
            )
            for row in rows
        ]
    except Exception as exc:
        logger.error(f"Error listing operator strategies: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list operator strategies",
        ) from exc


@router.post("/strategies/{governance_strategy_id}/lifecycle", response_model=OperatorStrategyResponse)
async def update_strategy_lifecycle(
    governance_strategy_id: str,
    request: LifecycleUpdateRequest,
) -> OperatorStrategyResponse:
    """Move a strategy through an allowed lifecycle transition."""
    current = governance_repository.get_strategy(governance_strategy_id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Governance strategy {governance_strategy_id} not found",
        )

    previous_state = StrategyLifecycleState(current.current_lifecycle_state.upper())
    next_state = request.lifecycle_state
    try:
        transition_validator.validate(
            previous_state=previous_state,
            next_state=next_state,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    governance_repository.update_strategy_lifecycle_state(
        strategy_id=governance_strategy_id,
        lifecycle_state=next_state.value,
    )
    strategies = await list_operator_strategies()
    for strategy in strategies:
        if strategy.governance_strategy_id == governance_strategy_id:
            return strategy
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Operational strategy for {governance_strategy_id} not found",
    )
