"""FastAPI application factory and entrypoint (``uvicorn api.main:app``).

Wires the routers, CORS and the domain-error handler, and runs the pipeline
job queue for the app's lifetime via the lifespan. The pipeline is composed
(never modified) through ``build_runner``; the queue is built once and shared
on ``app.state``.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.db.base import SessionLocal
from api.exceptions import APIError
from api.factory import build_runner
from api.routers import cases, documents, segments
from api.services import JobQueue, PipelineJobQueue
from api.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts the background worker on startup, stops it on shutdown."""
    queue: JobQueue = app.state.job_queue
    queue.start()
    try:
        yield
    finally:
        queue.stop()


def create_app(settings: Settings | None = None, job_queue: JobQueue | None = None) -> FastAPI:
    """Builds the app. Tests pass a test ``job_queue`` (and override the session)."""
    settings = settings or get_settings()
    app = FastAPI(title="mindocu API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Cross-origin JS (pdf.js) can only read these response headers if they
        # are explicitly exposed. Accept-Ranges/Content-Range let pdf.js detect
        # range support and load PDFs progressively instead of all-at-once. A
        # "*" wildcard is ignored here because allow_credentials=True forces an
        # explicit list.
        expose_headers=[
            "Accept-Ranges",
            "Content-Range",
            "Content-Length",
            "Content-Disposition",
            "ETag",
            "Last-Modified",
        ],
    )

    app.state.settings = settings
    app.state.job_queue = job_queue or PipelineJobQueue(build_runner(settings), SessionLocal)

    app.add_exception_handler(APIError, _api_error_handler) # type: ignore[arg-type] 
    app.include_router(cases.router)
    app.include_router(documents.router)
    app.include_router(segments.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Maps a domain error to its HTTP status with a JSON ``detail`` body."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app = create_app()
