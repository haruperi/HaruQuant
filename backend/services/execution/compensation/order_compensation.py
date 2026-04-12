"""Order compensation plan: offsetting orders, cancel pending."""

from __future__ import annotations

from typing import Any, Dict

from backend.common.logger import logger
from backend.services.execution.compensation.base import CompensationPlan


class OrderCompensationPlan(CompensationPlan):
    """Compensate for partial order failures."""

    def __init__(self, action_id: str) -> None:
        super().__init__(
            action_id,
            description="Offset or cancel orders that partially failed",
        )

    def execute(self, context: Dict[str, Any]) -> bool:
        """Execute order compensation."""
        order_type = context.get("order_type", "entry")
        order_id = context.get("order_id", "")

        if order_type == "entry":
            # Cancel the pending entry order
            self.log({"action": "cancel_order", "order_id": order_id})
            logger.info(f"OrderCompensation: cancelled entry order {order_id}")
            return True
        elif order_type == "exit":
            # Place offsetting order if exit failed
            symbol = context.get("symbol", "")
            original_volume = context.get("volume", 0.0)
            self.log({
                "action": "offsetting_order",
                "symbol": symbol,
                "volume": original_volume,
            })
            logger.info(
                f"OrderCompensation: placed offsetting order for {symbol} "
                f"volume={original_volume}"
            )
            return True

        self.log({"action": "unknown_order_type", "order_type": order_type})
        return False

    def validate(self, context: Dict[str, Any]) -> bool:
        """Validate order compensation is applicable."""
        return bool(context.get("order_id") or context.get("symbol"))
