"""Execution receipt normalization and persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.common.ids import generate_id
from backend.common.logger import logger
from backend.data.database import ExecutionReceiptRecord, ExecutionRepository
from backend.mcp.mt5_mcp import normalize_broker_response


@dataclass(frozen=True)
class NormalizedExecutionReceipt:
    """Normalized broker receipt plus persisted execution record."""

    normalized_payload: dict[str, Any]
    record: ExecutionReceiptRecord


class ExecutionReceiptService:
    """Normalize broker responses and persist canonical execution receipts."""

    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository
        logger.debug("ExecutionReceiptService initialized", component="execution.receipts")

    def persist_receipt(
        self,
        *,
        execution_intent_id: str,
        broker_response: Any,
        raw_receipt_ref: str | None = None,
    ) -> NormalizedExecutionReceipt:
        normalized = normalize_broker_response(broker_response)
        status = str(normalized["status"]).upper()

        logger.info(
            "Persisting execution receipt",
            component="execution.receipts",
            execution_intent_id=execution_intent_id,
            receipt_status=status,
            broker_order_id=normalized.get("order_id"),
            broker_deal_id=normalized.get("deal_id"),
        )
        if status not in {"FILLED", "DONE", "OK"}:
            logger.warning(
                "Non-success receipt status from broker",
                component="execution.receipts",
                execution_intent_id=execution_intent_id,
                receipt_status=status,
                broker_message=normalized.get("comment"),
                broker_retcode=normalized.get("retcode"),
            )

        record = self._repository.add_receipt(
            receipt_id=generate_id("receipt"),
            execution_intent_id=execution_intent_id,
            receipt_status=status,
            broker_order_id=None if normalized["order_id"] is None else str(normalized["order_id"]),
            broker_deal_id=None if normalized["deal_id"] is None else str(normalized["deal_id"]),
            raw_receipt_ref=raw_receipt_ref,
            broker_message=normalized.get("comment"),
            broker_retcode=normalized.get("retcode"),
            authoritative_state="PROVISIONAL",
        )
        return NormalizedExecutionReceipt(
            normalized_payload=normalized,
            record=record,
        )

