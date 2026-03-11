"""SSE events route."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.events import event_bus

router = APIRouter(prefix="/api")


@router.get("/events")
async def sse_events():
    """SSE endpoint for real-time updates.

    Clients connect here to receive live updates about:
    - Title generation (when a session gets its title)
    - Future: session deletions, agent status, etc.
    """

    async def event_stream():
        async for event in event_bus.subscribe():
            yield event.to_sse()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

