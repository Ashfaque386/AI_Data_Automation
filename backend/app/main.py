"""
Enterprise Data Operations Platform - FastAPI Main Application
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import structlog
import time

from app.config import settings
from app.database import Base, app_engine
from app.core.rbac import initialize_rbac
from app.database import get_app_db_context

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("application_startup", version=settings.APP_VERSION)
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=app_engine)
        
        # Initialize RBAC (roles and permissions)
        with get_app_db_context() as db:
            initialize_rbac(db)
        logger.info("database_initialized")
    except Exception as e:
        logger.warning("database_init_failed", error=str(e))
        logger.info("waiting_for_configuration")
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Data Operations Platform - Excel + SQL + AI",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request timing to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning("validation_error", errors=exc.errors(), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Validation error"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "message": "Enterprise Data Operations Platform API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Import and include routers
from app.api import auth, datasets, sql, export, users, ai, setup, ai_routes, edit_operations, connections

# Setup router is always available
app.include_router(setup.router, prefix="/api/setup", tags=["Setup"])

# Protected routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(connections.router, prefix="/api/connections", tags=["Connections"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["Datasets"])
app.include_router(edit_operations.router, prefix="/api/datasets", tags=["Edit Operations"])
app.include_router(sql.router, prefix="/api/sql", tags=["SQL"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(ai.router, prefix="/api/ai-legacy", tags=["AI (Legacy)"])
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI Configuration"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
