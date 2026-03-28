from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.logging import configure_logging

configure_logging()

from app.api.routes.citations import router as citations_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.query import router as query_router


def create_app() -> FastAPI:
    app = FastAPI(title="NASA Manual QA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(ingest_router, prefix="/api", tags=["ingest"])
    app.include_router(query_router, prefix="/api", tags=["query"])
    app.include_router(citations_router, prefix="/api", tags=["citations"])

    # Serve the vanilla HTML/JS frontend from the project root `frontend/` directory.
    # This "binds" frontend and backend to the same host/port.
    project_root = Path(__file__).resolve().parents[2]
    frontend_dir = project_root / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    return app


app = create_app()
