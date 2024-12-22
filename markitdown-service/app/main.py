import time
import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
import os
from app.api.v1.endpoints import conversion
from app.core.security.api_key import get_api_key
from app.db.init_db import ensure_db_initialized
from app.db.session import get_db, get_db_session
from app.core.config.settings import settings
from app.core.rate_limiting.limiter import limiter
from app.core.logging.config import get_web_logging_config
from app.core.audit import audit_log, AuditAction

# Initialize logging
os.makedirs(settings.LOG_DIR, exist_ok=True)
logging.config.dictConfig(get_web_logging_config())

# Create module-specific loggers
logger = logging.getLogger(__name__)
api_logger = logging.getLogger("app.api")
db_logger = logging.getLogger("app.db")
security_logger = logging.getLogger("app.core.security")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    try:
        logger.info("Starting application initialization...")
        
        # Log detailed configuration in debug mode
        logger.debug("Application configuration:")
        logger.debug(f"Environment: {settings.ENVIRONMENT}")
        logger.debug(f"Log Level: {settings.LOG_LEVEL}")
        logger.debug(f"API Key Auth: {settings.API_KEY_AUTH_ENABLED}")
        logger.debug(f"Rate Limit: {settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}")
        
        # Initialize database
        logger.info("Initializing database...")
        ensure_db_initialized()
        
        # Log startup status
        logger.info(f"Application started successfully in {settings.ENVIRONMENT} mode")
        
        # Audit log startup with detailed environment info
        audit_log(
            action=AuditAction.SERVICE_STARTUP,
            user_id=None,
            details={
                "environment": settings.ENVIRONMENT,
                "log_level": settings.LOG_LEVEL,
                "api_auth_enabled": settings.API_KEY_AUTH_ENABLED,
                "version": settings.VERSION
            }
        )
        
    except Exception as e:
        logger.critical(f"Failed to initialize application: {str(e)}", exc_info=True)
        audit_log(
            action=AuditAction.SERVICE_STARTUP,
            user_id=None,
            details={"error": str(e)},
            status="failure"
        )
        raise
    
    yield  # Server is running
    
    # Shutdown
    logger.info("Initiating application shutdown...")
    try:
        # Perform cleanup tasks here if needed
        audit_log(
            action=AuditAction.SERVICE_SHUTDOWN,
            user_id=None,
            details={"shutdown_type": "graceful"}
        )
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
        audit_log(
            action=AuditAction.SERVICE_SHUTDOWN,
            user_id=None,
            details={"error": str(e)},
            status="failure"
        )

# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A service for converting various file formats to Markdown",
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Custom rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request, exc):
    """Handle rate limit exceeded exceptions."""
    now = int(time.time())
    if settings.RATE_LIMIT_PERIOD == "minute":
        window_seconds = 60
    elif settings.RATE_LIMIT_PERIOD == "hour":
        window_seconds = 3600
    else:
        window_seconds = 60  # Default to minute if unknown period
        
    window_reset = now + window_seconds
    
    # Log rate limit violation with client info
    security_logger.warning(
        "Rate limit exceeded",
        extra={
            "client_ip": get_remote_address(request),
            "path": request.url.path,
            "reset_time": window_reset
        }
    )
    
    audit_log(
        action=AuditAction.RATE_LIMIT_EXCEEDED,
        user_id=None,
        details={
            "client_ip": get_remote_address(request),
            "path": request.url.path,
            "reset_time": window_reset
        },
        status="failure"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "type": "rate_limit_exceeded"
        },
        headers={
            "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(window_reset),
            "Retry-After": str(window_seconds)
        }
    )

# Include routers with API key dependency
app.include_router(
    conversion.router,
    prefix=settings.API_V1_STR,
    tags=["conversion"],
    dependencies=[Depends(get_api_key)] if settings.API_KEY_AUTH_ENABLED else None
)

# Health check endpoint (no API key required)
@app.get("/health", tags=["system"])
async def health_check():
    """Check the health of the service."""
    try:
        # Verify database connection using context manager
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
            db_logger.debug("Database health check successful")
        
        health_status = {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "auth_enabled": settings.API_KEY_AUTH_ENABLED,
            "supported_formats": settings.SUPPORTED_EXTENSIONS,
            "database": "connected",
            "rate_limit": {
                "requests": settings.RATE_LIMIT_REQUESTS,
                "period": settings.RATE_LIMIT_PERIOD
            }
        }
        
        # Log health check with detailed status in debug mode
        logger.debug("Health check details", extra=health_status)
        
        audit_log(
            action=AuditAction.HEALTH_CHECK,
            user_id=None,
            details=health_status
        )
        
        return health_status
    except Exception as e:
        error_details = {
            "status": "unhealthy",
            "version": settings.VERSION,
            "error": str(e)
        }
        
        logger.error(
            "Health check failed",
            exc_info=True,
            extra=error_details
        )
        
        audit_log(
            action=AuditAction.HEALTH_CHECK,
            user_id=None,
            details=error_details,
            status="failure"
        )
        
        return JSONResponse(
            status_code=503,
            content=error_details
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        log_config=get_web_logging_config(),
        workers=1
    )