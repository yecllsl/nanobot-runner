"""运行时事件 SSE 端点 (v0.32.0)

提供 Server-Sent Events 流式推送，将 Agent 运行时事件
（迭代开始、工具调用等）实时推送到 WebUI 前端。
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.core.transparency.runtime_event_hook import RuntimeEvent
from src.core.webui.auth import get_current_user

router = APIRouter()


@router.get("/runtime-events/stream")
async def stream_runtime_events(
    request: Request,
    user: str = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式推送运行时事件

    客户端通过 EventSource 连接此端点，接收实时运行时事件。
    事件格式：data: {"type": "iteration_start", "trace_id": "...", "data": ...}\\n\\n
    """
    runtime_hook = request.app.state.runtime_event_hook

    async def event_generator():
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue()

        def callback(event: RuntimeEvent) -> None:
            queue.put_nowait(event)

        runtime_hook.subscribe(callback)

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    event_data = {
                        "type": event.type,
                        "trace_id": event.trace_id,
                        "data": event.data,
                    }
                    yield f"data: {json.dumps(event_data, default=str)}\n\n"
                except TimeoutError:
                    # 发送心跳保活
                    yield ": heartbeat\n\n"
        finally:
            if callback in runtime_hook._subscribers:
                runtime_hook._subscribers.remove(callback)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
