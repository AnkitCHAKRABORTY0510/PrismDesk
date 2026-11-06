from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.api.router import api_router

from app.database.session import engine

# --------------------------------------------------
# FastAPI Application Configuration
# --------------------------------------------------

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
    - Audit History
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# --------------------------------------------------
# System Endpoints
# --------------------------------------------------

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
