import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import ServiceError
from app.core.logging import configure_logging
from app.database.session import engine

configure_logging()
logger = logging.getLogger("prism_desk")

app = FastAPI(
    title="Prism Desk API",
    description="""
    REST API for Prism Desk.

    Laboratory Management and Research Collaboration Platform.

    Modules:
    - Authentication
    - User Management
    - Roles and Permissions
    - Project Management
    - Research Library
    - Task Management
    - Daily Research Handbook
    - Conference Tracker
    - Discord Notifications
    - Dashboards
    - Audit History

    State-changing requests authenticated by the session cookie must send
    the `X-CSRF-Token` header returned by `/api/v1/auth/login` and
    `/api/v1/auth/me`.
    """,
    version="1.0.0",
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.API_DOCS_ENABLED else None,
)

# Registered before CORSMiddleware so it runs *inside* it: unexpected errors
# become a JSON 500 that still carries CORS headers, so the browser shows a
# real error instead of a network failure ("Cannot reach the server").
@app.middleware("http")
async def unexpected_error_as_json(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "The server hit an unexpected error. Details are in the backend log."},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", settings.CSRF_HEADER_NAME],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, error: ServiceError):
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail},
    )


app.include_router(api_router)


@app.get("/", tags=["System"])
def root():
    return {
        "application": "Prism Desk",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["System"])
def health():
    return {
        "application": "Prism Desk",
        "status": "healthy",
    }


@app.get("/health/database", tags=["System"])
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "application": "Prism Desk",
            "database": "PostgreSQL",
            "status": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        )
