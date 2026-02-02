"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from config import settings
from api import chat, parts, compatibility, cart
from database import init_db

# Setup logging
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting PartSelect Chat Agent API")
    init_db()
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
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PartSelect Chat Agent API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    import os
    # Use PORT from environment (Railway/Render) or fallback to config
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=settings.environment == "development"
    )
