"""Bizz AI FastAPI application entrypoint."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.services.errors import ConflictError, NotFoundError, ReferenceError

logger = logging.getLogger("bizzai")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Versioned API.
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    @app.get("/health", include_in_schema=False)
    def root_health() -> dict[str, str]:
        """Unversioned liveness probe for containers/orchestration."""
        return {"status": "ok"}

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ReferenceError)
    async def reference_handler(_request: Request, exc: ReferenceError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def db_exception_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Return a safe 503 for database failures; log internals server-side."""
        logger.error("Database error: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Database unavailable"},
        )

    return app


app = create_app()
