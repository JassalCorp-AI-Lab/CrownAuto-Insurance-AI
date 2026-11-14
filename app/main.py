"""Application entry point.

Run:  uv run uvicorn app.main:app --reload

`create_app()` builds the FastAPI app: it creates the ChatService once at
startup, registers the API routers and serves the chat UI from /static.
"""

import logging
import threading
from contextlib import asynccontextmanager

import pyfiglet
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, health
from app.core.config import ROOT_DIR, get_settings
from app.knowledge.vector_store import get_vector_store
from app.services.chat_service import ChatService
from app.workflow import build_graph

STATIC_DIR = ROOT_DIR / "static"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("crownauto")


def _warm_up_knowledge_base() -> None:
    try:
        get_vector_store().warm_up()
    except Exception as e:
        log.warning("Knowledge base not indexed yet (%s). Will retry on first question.", e)


def _print_banner() -> None:
    print(pyfiglet.figlet_format("CrownAuto"), flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _print_banner()
    settings = get_settings()
    app.state.chat_service = ChatService(build_graph(), settings.graph_recursion_limit)

    if settings.openai_api_key:
        # Embed/load the KB in the background so startup stays instant.
        threading.Thread(target=_warm_up_knowledge_base, daemon=True).start()
    else:
        log.warning("OPENAI_API_KEY is not set — the UI will load but chat will fail. See .env.example")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="CrownAuto Insurance AI", version="0.2.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
