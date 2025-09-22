"""
Simplified API Router for Basic Integration
"""

from fastapi import APIRouter
from app.api.v1.endpoints.simple_file_controller import router as files_router

api_router = APIRouter()

# Include file management routes
api_router.include_router(files_router, prefix="/files", tags=["files"])
