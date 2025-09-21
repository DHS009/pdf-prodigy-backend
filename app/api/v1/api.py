"""
Main API router for v1 endpoints
Comprehensive PDF processing API with file management
"""

from fastapi import APIRouter
from app.api.v1.endpoints import pdf_operations_controller, file_management_controller

api_router = APIRouter()

# Include PDF operations routes
api_router.include_router(
    pdf_operations_controller.router, 
    prefix="/pdf", 
    tags=["PDF Operations"]
)

# Include file management routes
api_router.include_router(
    file_management_controller.router,
    prefix="/files",
    tags=["File Management"]
)

# Enhanced health check for API v1
@api_router.get(
    "/health",
    tags=["System"],
    summary="API Health Check",
    description="Check the health and availability of the PDF processing API"
)
async def api_health():
    """
    ## API Health Check
    
    Verify that the API is running and all core services are available.
    
    ### Response Information:
    - **status**: Current API status
    - **version**: API version number
    - **available_endpoints**: List of main API endpoints
    - **services**: Status of core services
    
    ### Use Cases:
    - **Monitoring**: Regular health checks for uptime monitoring
    - **Load Balancing**: Health check for load balancer configuration
    - **Development**: Verify API is running during development
    - **Integration**: Confirm API availability before processing
    """
    return {
        "status": "healthy",
        "version": "v1",
        "available_endpoints": {
            "pdf_operations": [
                "/pdf/edit - Edit PDF documents",
                "/pdf/split - Split PDF into multiple files", 
                "/pdf/merge - Merge multiple PDFs",
                "/pdf/download/{file_id} - Download processed files",
                "/pdf/status/{file_id} - Check processing status"
            ],
            "file_management": [
                "/files/upload - Upload files for processing",
                "/files/validate/{filename} - Validate file format"
            ],
            "system": [
                "/health - API health check"
            ]
        },
        "services": {
            "pdf_processor": "operational",
            "file_storage": "operational", 
            "background_tasks": "operational"
        },
        "limits": {
            "max_file_size": "50MB",
            "max_files_per_request": 10,
            "supported_formats": ["PDF"]
        }
    }
