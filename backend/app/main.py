import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.db.init_db import init_db


def normalize_mount_path(path: str) -> str:
    normalized = path.strip()
    if not normalized or normalized == "/":
        return "/"
    return "/" + normalized.strip("/")


def normalize_base_href(path: str) -> str:
    normalized = normalize_mount_path(path)
    if normalized == "/":
        return "/"
    return f"{normalized}/"


def sync_index_base_href(static_files_dir: Path, ui_prefix: str) -> None:
    index_path = static_files_dir / "index.html"
    if not index_path.is_file():
        return

    html = index_path.read_text(encoding="utf-8")
    base_href = normalize_base_href(ui_prefix)
    updated_html = re.sub(r'<base\s+href="[^"]*"\s*/?>', f'<base href="{base_href}">', html)
    if updated_html != html:
        index_path.write_text(updated_html, encoding="utf-8")


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
        ui_prefix = normalize_mount_path(settings.ui_prefix)
        sync_index_base_href(static_files_dir, settings.ui_prefix)
        if ui_prefix != "/":

            @app.get(ui_prefix, include_in_schema=False)
            def serve_ui_index() -> FileResponse:
                return FileResponse(static_files_dir / "index.html")

        app.mount(
            ui_prefix,
            StaticFiles(directory=static_files_dir, html=True),
            name="web",
        )

    return app


app = create_app()
