"""
API Version 1 Package

Contains all version 1 API components including:
- endpoints: API route controllers
- models: Request/response data models (if separate)
- schemas: Data validation schemas (if needed)

This follows semantic versioning for API compatibility.
"""

from . import endpoints
from .api import api_router

__all__ = [
    "endpoints", 
    "api_router"
]

__version__ = "1.0.0"
