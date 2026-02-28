"""
Invoice Enterprise Console - FastAPI Application

Production-grade enterprise invoice management system.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import logger, request_id_ctx, setup_logging
from app.core.security import generate_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize database (create tables if needed in dev)
    if settings.environment == "development":
        await init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Enterprise-grade invoice management and automation system",
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for tracking."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    request_id_ctx.set(request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    request_id = request_id_ctx.get() or "N/A"
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - verifies database connection."""
    from app.core.database import async_session_factory
    from sqlalchemy import text
    
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Root redirect
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/api/docs",
        "version": settings.app_version,
    }
