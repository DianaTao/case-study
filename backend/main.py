"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import os

from config import settings
from api import chat, parts, compatibility, cart
from database import init_db, get_db

# Setup logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting PartSelect Chat Agent API")
    try:
        init_db()
        logger.info("Database connection initialized")
        logger.info("Application startup complete")
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise
    yield
    logger.info("Shutting down")


# Create FastAPI app
app = FastAPI(
    title="PartSelect Chat Agent API",
    description="Backend API for PartSelect chat assistant with real scraped data",
    version="1.0.0",
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

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(parts.router, prefix="/api/parts", tags=["parts"])
app.include_router(compatibility.router, prefix="/api/compatibility", tags=["compatibility"])
app.include_router(cart.router, prefix="/api/cart", tags=["cart"])


@app.get("/")
async def root():
    """Root endpoint - simple health check for Railway."""
    return {
        "status": "ok",
        "service": "PartSelect Chat Agent API",
        "version": "1.0.0",
        "message": "API is running"
    }


@app.get("/health")
async def health():
    """Detailed health check - lightweight version for Railway."""
    try:
        # Lightweight check - don't query DB to avoid timeouts
        db = get_db()
        db_status = "connected" if db is not None else "disconnected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "environment": settings.environment,
            "port": os.getenv("PORT", "unknown")
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "database": "unknown",
            "environment": settings.environment,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    import os
    # Use PORT from environment (Railway/Render) or fallback to config
    port = int(os.getenv("PORT", settings.port))
    # Disable reload in production (Railway/Render)
    is_development = os.getenv("ENVIRONMENT", "production").lower() == "development"
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=is_development,
        log_level="info"
    )
