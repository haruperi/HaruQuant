"""SSE event stream for the operator dashboard."""

from __future__ import annotations

import json

from fastapi import APIRouter
from starlette.responses import StreamingResponse


router = APIRouter(prefix="/api/operator/events", tags=["events"])


def _sse_messages():
    events = [
        {"type": "workflow", "message": "wf_trade_review_001 entered RECONCILING"},
        {"type": "approval", "message": "appr_live_exec_001 awaiting final approver"},
        {"type": "incident", "message": "inc_001 remains OPEN pending broker review"},
    ]
    for event in events:
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/stream")
def stream_operator_events() -> StreamingResponse:
    return StreamingResponse(_sse_messages(), media_type="text/event-stream")
