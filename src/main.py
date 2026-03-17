from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.v1.todos import router as todos_router
from src.config import get_settings
from src.repositories.memory import InMemoryTodoRepository
from src.services.todo_service import TodoService


def configure_logging(log_level: str = "INFO", loki_url: str = "") -> None:
    """Configure structlog to emit JSON on stdout.

    Every log line includes timestamp, level, logger name, and any context
    variables bound via structlog.contextvars (e.g. request_id).
    If loki_url is set, also pushes logs directly to Loki via HTTP.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level)

    if loki_url:
        import logging_loki

        logging_loki.emitter.LokiEmitter.level_tag = "level"
        loki_handler = logging_loki.LokiHandler(
            url=loki_url,
            tags={"container": "sample-app", "env": "dev"},
            version="1",
        )
        loki_handler.setLevel(level)
        logging.getLogger().addHandler(loki_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _build_repository(settings: object) -> InMemoryTodoRepository:
    from src.config import Settings

    s = settings if isinstance(settings, Settings) else get_settings()
    match s.storage.backend:
        case "memory":
            return InMemoryTodoRepository()
        case _:
            raise ValueError(
                f"Unknown storage backend '{s.storage.backend}'. "
                "Supported: 'memory'. See docs/repository-pattern.md for extending."
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    configure_logging(settings.app.log_level, settings.app.loki_url)
    logger = structlog.get_logger(__name__)

    repo = _build_repository(settings)
    service = TodoService(repo)
    await service.sync_active_gauge()
    app.state.service = service

    logger.info(
        "app_started",
        host=settings.app.host,
        port=settings.app.port,
        storage_backend=settings.storage.backend,
    )
    yield
    logger.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Todo App",
        description="Demo todo list with Prometheus/Grafana/Loki monitoring",
        version="0.1.0",
        debug=settings.app.debug,
        lifespan=lifespan,
    )

    # Prometheus — register before routers so /metrics is available immediately
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, include_in_schema=False)

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Routes
    app.include_router(todos_router)

    # Request-ID middleware for log correlation
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Health-check endpoint
    @app.get("/health", include_in_schema=False)
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
