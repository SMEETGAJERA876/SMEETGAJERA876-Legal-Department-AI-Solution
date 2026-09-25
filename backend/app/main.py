import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import account, document_check, documents, health, summary
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import check_production_settings, security_middleware
from app.services.lifecycle import PeriodicJobs

logger = logging.getLogger("clauselens")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Resume documents interrupted by a restart, then apply retention periodically.
    jobs = PeriodicJobs()
    jobs.start()
    yield
    jobs.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    check_production_settings(settings)
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.middleware("http")(security_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Lets the browser read download file names from API responses.
        expose_headers=["Content-Disposition"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"error": exc.code, "message": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = ", ".join(str(err["loc"][-1]) for err in exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_request",
                "message": f"Some information in the request is missing or invalid ({fields}).",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces to clients.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "The server hit an unexpected problem. Please try again shortly.",
            },
        )

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(document_check.router)
    app.include_router(summary.router)
    app.include_router(account.router)
    return app


app = create_app()
