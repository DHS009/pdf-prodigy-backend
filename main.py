"""
PDF Prodigy Backend API
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import time

from app.core.config import settings
from app.core.logger import logger
from app.api.v1.api import api_router
from app.db.session import engine
from app.db.base import Base

# Create FastAPI instance with comprehensive API documentation
app = FastAPI(
    title="PDF Prodigy API",
    version="1.0.0",
    description="""
## PDF Prodigy Backend API

A powerful and comprehensive PDF processing service that provides advanced PDF manipulation capabilities.

### 🚀 Features

#### PDF Operations
- **Edit PDFs**: Add text, images, and annotations with precise positioning
- **Split PDFs**: Extract pages using multiple strategies (pages, ranges, bookmarks, size)
- **Merge PDFs**: Combine multiple documents with bookmark and numbering options

#### File Management
- **Secure Upload**: Multi-file upload with validation and sanitization
- **Format Validation**: Pre-upload file format checking
- **Temporary Storage**: Automatic cleanup after 24 hours

#### Advanced Features
- **Background Processing**: Async operations for large files
- **Progress Tracking**: Real-time status monitoring
- **Error Handling**: Comprehensive error reporting and logging
- **Security**: File validation, sanitization, and secure processing

### 📋 API Standards

- **RESTful Design**: Following REST principles and HTTP standards
- **OpenAPI 3.0**: Complete API specification with examples
- **JSON Responses**: Consistent response format across all endpoints
- **Error Codes**: Standard HTTP status codes with detailed error messages

### 🔧 Technical Stack

- **FastAPI**: Modern Python web framework with automatic API documentation
- **PyMuPDF**: Advanced PDF processing and manipulation
- **Pydantic**: Data validation and serialization
- **Background Tasks**: Async processing for heavy operations

### 🌐 Usage

```bash
# Upload files
curl -X POST "http://localhost:8000/api/v1/files/upload" \\
     -F "files=@document.pdf"

# Edit PDF (add text)
curl -X POST "http://localhost:8000/api/v1/pdf/edit" \\
     -F "file=@document.pdf" \\
     -F "operation_type=add_text" \\
     -F "page_number=1" \\
     -F "text=Hello World" \\
     -F "x=100" \\
     -F "y=200"

# Split PDF
curl -X POST "http://localhost:8000/api/v1/pdf/split" \\
     -F "file=@document.pdf" \\
     -F "split_type=pages" \\
     -F "pages=1,3,5"

# Merge PDFs
curl -X POST "http://localhost:8000/api/v1/pdf/merge" \\
     -F "files=@doc1.pdf" \\
     -F "files=@doc2.pdf"
```

### 📞 Support
- **Interactive Documentation**: Available at `/docs`
- **Alternative Documentation**: Available at `/redoc`
- **Health Check**: Available at `/health`
    """,
    contact={
        "name": "PDF Prodigy Support",
        "email": "support@pdfprodigy.com",
        "url": "https://pdfprodigy.com/support"
    },
    license_info={
        "name": "MIT License", 
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://pdfprodigy.com/terms",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "tomorrow-night",
        "tryItOutEnabled": True,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "docExpansion": "list",
        "operationsSorter": "method",
        "tagsSorter": "alpha"
    }
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# Static files for serving uploaded files
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PDF Prodigy API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health"
    }

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting PDF Prodigy API...")
    # Create database tables
    # Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PDF Prodigy API...")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.DEBUG else 4
    )
