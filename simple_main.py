"""
Simplified PDF Prodigy Backend for Basic Integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.simple_config import settings
from app.core.simple_logger import logger
from app.api.v1.simple_api import api_router

# Create FastAPI instance
app = FastAPI(
    title="PDF Prodigy API",
    version="1.0.0",
    description="A simple PDF processing service for basic integration",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PDF Prodigy API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    logger.info("Starting PDF Prodigy API...")
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
