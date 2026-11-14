"""FastAPI dependencies shared by routes.

The ChatService is created once at startup (see app/main.py) and stored on
`app.state`. Routes receive it via `Depends(get_chat_service)`, which also
lets tests swap in a fake service with `app.dependency_overrides`.
"""

from fastapi import Request

from app.services.chat_service import ChatService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
