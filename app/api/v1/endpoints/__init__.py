"""
API Endpoints Package

This package contains all API endpoint controllers following Java naming conventions.
Each controller handles specific domain operations:

- pdf_operations_controller: Core PDF processing (edit, split, merge)
- file_management_controller: File upload, validation, and management

Usage:
    from app.api.v1.endpoints import pdf_operations_controller
    from app.api.v1.endpoints import file_management_controller
"""

# Import controllers for easy access
from . import pdf_operations_controller
from . import file_management_controller

# Define what gets imported with "from endpoints import *"
__all__ = [
    "pdf_operations_controller",
    "file_management_controller"
]

# Package metadata
__version__ = "1.0.0"
__author__ = "PDF Prodigy Team"
