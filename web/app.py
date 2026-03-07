from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.routes.api import router as api_router
from web.routes.webhooks import router as webhooks_router

STATIC_DIR = Path(__file__).resolve().parent / "static" / "mini_app"
INDEX_HTML = STATIC_DIR / "index.html"


def create_app(lifespan: Any = None) -> FastAPI:
    kwargs: dict = {"title": "TelegramPayBot", "docs_url": None, "redoc_url": None}
    if lifespan is not None:
        kwargs["lifespan"] = lifespan
    app = FastAPI(**kwargs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(webhooks_router)

    @app.get("/mini_app")
    @app.get("/mini_app/")
    def serve_mini_app():
        if INDEX_HTML.exists():
            return FileResponse(INDEX_HTML, media_type="text/html")
        return {"error": "Mini App not found"}, 404

    app.mount("/mini_app", StaticFiles(directory=str(STATIC_DIR), html=True), name="mini_app")

    return app
