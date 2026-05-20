from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.container import get_container

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    container = get_container()
    app = FastAPI(
        title="AI Styling Agent Backend",
        version="0.1.0",
        description="Workflow + expert-agent graph backend for high-quality clothing recommendation and try-on images.",
    )
    container.settings.storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/objects", StaticFiles(directory=container.settings.storage_dir), name="objects")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def app_shell() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
