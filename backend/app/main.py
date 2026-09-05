from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.db.init_db import init_db


def normalize_mount_path(path: str) -> str:
    normalized = path.strip()
    if not normalized or normalized == "/":
        return "/"
    return "/" + normalized.strip("/")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    static_files_dir = Path(settings.static_files_dir)
    if static_files_dir.exists():
        app.mount(
            normalize_mount_path(settings.ui_prefix),
            StaticFiles(directory=static_files_dir, html=True),
            name="web",
        )

    return app


app = create_app()
