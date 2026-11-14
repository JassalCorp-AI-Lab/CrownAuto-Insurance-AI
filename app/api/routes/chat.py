"""Chat endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_chat_service
from app.api.forms import chat_form
from app.api.schemas import ChatInput, ChatResponse, OkResponse
from app.services.chat_service import ChatError, ChatService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
def chat_stream(payload: ChatInput = Depends(chat_form), service: ChatService = Depends(get_chat_service)):
    """Stream a reply as Server-Sent Events — one JSON event per graph step."""

    def sse_events():
        for event in service.stream(payload.message, payload.session_id, payload.image_data_url):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatInput = Depends(chat_form), service: ChatService = Depends(get_chat_service)):
    """Return the final reply as JSON (blocking)."""
    try:
        # The graph is synchronous; run it in a worker thread so the server stays responsive.
        return await run_in_threadpool(service.send, payload.message, payload.session_id, payload.image_data_url)
    except ChatError as e:
        raise HTTPException(502, str(e)) from e


@router.delete("/session/{session_id}", response_model=OkResponse)
def delete_session(session_id: str, service: ChatService = Depends(get_chat_service)):
    """Forget a conversation (used by the UI's "New chat" button)."""
    service.reset(session_id)
    return OkResponse()
