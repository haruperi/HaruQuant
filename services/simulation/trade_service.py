"""Trade and order mutation helpers for simulator routes."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, status

from services.risk.simulation import HypotheticalOrderAction
from services.utils.logger import logger

from .route_support import (
    build_session_state_response,
    normalize_order,
    order_info_to_dict,
)
from .serializers import _serialize_governance_report, _serialize_what_if_comparison
from .session_runtime import SimulatorSession, _object_to_dict


def execute_trade(
    active: SimulatorSession,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    governance = _evaluate_trade_governance(
        active,
        symbol=str(request_payload.get("symbol") or active.symbols[0]).strip().upper()
        or active.symbols[0],
        signed_volume=_trade_signed_volume(
            str(request_payload.get("side") or "buy"),
            float(request_payload.get("volume") or 0.0),
        ),
        allow_manual_override=(
            str(active.config.get("mode", "manual") or "manual") == "manual"
            and bool(request_payload.get("manual_review_accepted"))
        ),
    )

    trade = active.execute_trade(request_payload)
    if not trade:
        raise HTTPException(status_code=500, detail="Trade execution failed")

    response = build_session_state_response(active)
    return {
        "trade": trade,
        "positions": response["positions"],
        "orders": response["orders"],
        "governance": _serialize_governance_report(governance)
        if governance is not None
        else active.get_governance_report(),
        "risk_snapshot": response["risk_snapshot"],
        "risk_scorecard": response["risk_scorecard"],
        "recommendations": response["recommendations"],
    }


def preview_trade(
    active: SimulatorSession,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(request_payload.get("symbol") or active.symbols[0]).strip().upper()
    symbol = symbol or active.symbols[0]
    signed_volume = _trade_signed_volume(
        str(request_payload.get("side") or "buy"),
        float(request_payload.get("volume") or 0.0),
    )
    return active.build_manual_trade_review(symbol=symbol, signed_volume=signed_volume)


def place_pending_order(
    active: SimulatorSession,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    governance = _evaluate_trade_governance(
        active,
        symbol=str(request_payload.get("symbol") or active.symbols[0]).strip().upper()
        or active.symbols[0],
        signed_volume=_pending_signed_volume(
            str(request_payload.get("type") or ""),
            float(request_payload.get("volume") or 0.0),
        ),
        allow_manual_override=False,
    )

    order = active.place_pending_order(request_payload)
    if not order:
        raise HTTPException(status_code=500, detail="Pending order failed")

    response = build_session_state_response(active)
    return {
        "order": order,
        "positions": response["positions"],
        "orders": response["orders"],
        "governance": _serialize_governance_report(governance)
        if governance is not None
        else active.get_governance_report(),
        "risk_snapshot": response["risk_snapshot"],
        "risk_scorecard": response["risk_scorecard"],
        "recommendations": response["recommendations"],
    }


def evaluate_what_if(
    active: SimulatorSession,
    actions_payload: list[Any],
    leverage_override: int | None,
    *,
    refresh_session_risk_state: Callable[[SimulatorSession], None],
) -> dict[str, Any]:
    refresh_session_risk_state(active)
    actions = [
        HypotheticalOrderAction(
            action_type=str(item.action_type or "").strip(),
            symbol=str(item.symbol or "").strip().upper(),
            delta_lots=item.delta_lots,
            target_lots=item.target_lots,
            rationale=str(item.rationale or ""),
        )
        for item in actions_payload
        if str(item.symbol or "").strip()
    ]
    comparison = active.evaluate_what_if(
        actions=actions,
        leverage_override=leverage_override,
    )
    storage_refs = active.persist_what_if_comparison(comparison)
    payload = _serialize_what_if_comparison(comparison)
    payload.update(storage_refs)
    return payload


def modify_position(
    active: SimulatorSession,
    *,
    session_id: int,
    position_id: int,
    sl: float | None,
    tp: float | None,
) -> dict[str, Any]:
    logger.info(
        f"Modify position request | session={session_id} position={position_id} "
        f"sl={sl} tp={tp}"
    )
    pos = active.simulator._positions_data.get(int(position_id))
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    pos_data = _object_to_dict(pos)
    ok = active.simulator.modify_position(
        pos_data,
        new_sl=sl if sl is not None else pos_data.get("sl", 0.0),
        new_tp=tp if tp is not None else pos_data.get("tp", 0.0),
    )
    if not ok:
        logger.error(
            f"Modify position failed | session={session_id} position={position_id}"
        )
        raise HTTPException(status_code=500, detail="Failed to modify position")
    return build_session_state_response(active)


def close_position(
    active: SimulatorSession,
    *,
    session_id: int,
    position_id: int,
) -> dict[str, Any]:
    logger.info(f"Close position request | session={session_id} position={position_id}")
    pos = active.simulator._positions_data.get(int(position_id))
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    pos_data = _object_to_dict(pos)
    ok = active.simulator.close_position(pos_data, reason="manual")
    if not ok:
        logger.error(f"Close position failed | session={session_id} position={position_id}")
        raise HTTPException(status_code=500, detail="Failed to close position")
    return build_session_state_response(active)


def partial_close_position(
    active: SimulatorSession,
    *,
    session_id: int,
    position_id: int,
    volume: float,
) -> dict[str, Any]:
    if volume <= 0:
        raise HTTPException(status_code=400, detail="Volume must be > 0")

    logger.info(
        f"Partial close request | session={session_id} position={position_id} volume={volume}"
    )
    pos = active.simulator._positions_data.get(int(position_id))
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    pos_data = _object_to_dict(pos)
    current_volume = float(pos_data.get("volume", 0.0) or 0.0)
    if volume >= current_volume:
        ok = active.simulator.close_position(pos_data, reason="manual")
    else:
        symbol = str(pos_data.get("symbol", "") or "")
        ticket = int(
            pos_data.get("ticket")
            or pos_data.get("position_id")
            or pos_data.get("identifier")
            or 0
        )
        result = active.simulator.trade_api.PositionClosePartial(
            symbol=symbol,
            ticket=ticket,
            volume=volume,
        )
        ok = int(getattr(result, "retcode", 0) or 0) in (10008, 10009)

    if not ok:
        logger.error(
            f"Partial close failed | session={session_id} position={position_id}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")
    return build_session_state_response(active)


def modify_order(
    active: SimulatorSession,
    *,
    session_id: int,
    order_id: int,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        f"Modify order request | session={session_id} order={order_id} "
        f"volume={request_payload.get('volume')} price={request_payload.get('price')} "
        f"sl={request_payload.get('sl')} tp={request_payload.get('tp')}"
    )

    order = active.simulator._orders_data.get(int(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order_data = _object_to_dict(order)
    normalized_order = normalize_order(order_info_to_dict(order))
    current_volume = float(
        order_data.get("volume_current") or order_data.get("volume_initial") or 0.0
    )
    request_volume = request_payload.get("volume")
    if request_volume is not None:
        if float(request_volume) <= 0:
            raise HTTPException(status_code=400, detail="Volume must be > 0")
        if float(request_volume) > current_volume:
            raise HTTPException(
                status_code=400,
                detail=f"Volume cannot exceed current order volume ({current_volume:.2f})",
            )

    new_price = (
        request_payload.get("price")
        if request_payload.get("price") is not None
        else order_data.get("open_price")
    )
    new_sl = float(
        request_payload.get("sl")
        if request_payload.get("sl") is not None
        else order_data.get("sl", 0.0)
    )
    new_tp = float(
        request_payload.get("tp")
        if request_payload.get("tp") is not None
        else order_data.get("tp", 0.0)
    )
    requested_volume = (
        float(request_volume) if request_volume is not None else current_volume
    )

    if request_volume is not None and abs(requested_volume - current_volume) > 1e-12:
        delete_ok = active.simulator.order_delete(order_data)
        if not delete_ok:
            logger.error(
                f"Delete order before recreate failed | session={session_id} order={order_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to modify order")

        recreated = active.place_pending_order(
            {
                "type": str(normalized_order.get("type", "") or ""),
                "volume": requested_volume,
                "price": float(new_price or 0.0),
                "sl": new_sl,
                "tp": new_tp,
                "comment": str(normalized_order.get("comment") or "Pending order"),
            }
        )
        if not recreated or int(recreated.get("retcode", 0) or 0) not in (10008, 10009):
            active.place_pending_order(
                {
                    "type": str(normalized_order.get("type", "") or ""),
                    "volume": current_volume,
                    "price": float(normalized_order.get("open_price") or 0.0),
                    "sl": float(normalized_order.get("sl") or 0.0),
                    "tp": float(normalized_order.get("tp") or 0.0),
                    "comment": str(normalized_order.get("comment") or "Pending order"),
                }
            )
            logger.error(f"Recreate order failed | session={session_id} order={order_id}")
            raise HTTPException(status_code=500, detail="Failed to modify order")
    else:
        ok = active.simulator.order_modify(
            order_data,
            new_open_price=float(new_price or 0.0),
            new_sl=new_sl,
            new_tp=new_tp,
        )
        if not ok:
            logger.error(f"Modify order failed | session={session_id} order={order_id}")
            raise HTTPException(status_code=500, detail="Failed to modify order")

    return build_session_state_response(active)


def delete_order(
    active: SimulatorSession,
    *,
    session_id: int,
    order_id: int,
) -> dict[str, Any]:
    logger.info(f"Delete order request | session={session_id} order={order_id}")
    order = active.simulator._orders_data.get(int(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order_data = _object_to_dict(order)
    ok = active.simulator.order_delete(order_data)
    if not ok:
        logger.error(f"Delete order failed | session={session_id} order={order_id}")
        raise HTTPException(status_code=500, detail="Failed to delete order")
    return build_session_state_response(active)


def _trade_signed_volume(side: str, volume: float) -> float:
    signed_volume = abs(float(volume or 0.0))
    if str(side or "buy").lower() == "sell":
        signed_volume *= -1.0
    return signed_volume


def _pending_signed_volume(order_type: str, volume: float) -> float:
    signed_volume = abs(float(volume or 0.0))
    if str(order_type or "").lower().startswith("sell"):
        signed_volume *= -1.0
    return signed_volume


def _evaluate_trade_governance(
    active: SimulatorSession,
    *,
    symbol: str,
    signed_volume: float,
    allow_manual_override: bool,
):
    governance = active.evaluate_pre_trade_governance(
        symbol=symbol,
        signed_volume=signed_volume,
    )
    if (
        active.risk_limits_enforced()
        and governance is not None
        and str(getattr(governance, "decision", "ACCEPT")) != "ACCEPT"
        and not allow_manual_override
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "governance_reject",
                "governance": _serialize_governance_report(governance),
            },
        )
    return governance
