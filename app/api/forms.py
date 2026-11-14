"""Parses and validates the chat form (text + optional photo upload).

Used as a FastAPI dependency: `payload: ChatInput = Depends(chat_form)`.
Any problem raises HTTPException, so routes only ever see valid input.
"""

import base64

from fastapi import File, Form, HTTPException, UploadFile

from app.api.schemas import ChatInput
from app.core.config import get_settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
DEFAULT_PHOTO_MESSAGE = "Here is a photo of the damage to my car."
MAX_SESSION_ID_LENGTH = 100


async def chat_form(
    message: str = Form(""),
    session_id: str = Form(...),
    image: UploadFile | None = File(None),
) -> ChatInput:
    image_data_url = await _read_image(image)
    message = message.strip()

    if not message and not image_data_url:
        raise HTTPException(400, "Message is empty.")
    if not session_id or len(session_id) > MAX_SESSION_ID_LENGTH:
        raise HTTPException(400, "Invalid session_id.")

    return ChatInput(
        message=message or DEFAULT_PHOTO_MESSAGE,
        session_id=session_id,
        image_data_url=image_data_url,
    )


async def _read_image(image: UploadFile | None) -> str | None:
    """Validate the upload and return it as a data URL, or None if absent."""
    if image is None or not image.filename:
        return None
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, f"Unsupported image type: {image.content_type}. Use JPEG, PNG, WebP or GIF.")

    data = await image.read()
    max_mb = get_settings().max_image_mb
    if not data:
        raise HTTPException(400, "Uploaded image is empty.")
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {max_mb:g} MB.")

    return f"data:{image.content_type};base64,{base64.b64encode(data).decode()}"
