"""
API Package

Root API package containing all API versions.
Currently supports:
- v1: Core PDF processing operations

Future versions can be added here while maintaining backward compatibility.

Usage:
    from app.api.v1 import api_router as v1_router
    from app.api.v2 import api_router as v2_router  # Future
"""

from . import v1

__all__ = ["v1"]

# API metadata
__version__ = "1.0.0"
__api_versions__ = ["v1"]
