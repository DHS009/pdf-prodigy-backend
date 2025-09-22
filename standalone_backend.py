"""
Standalone PDF Prodigy Backend for Basic Integration
This is a simplified version that doesn't depend on the complex app structure
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List
import uvicorn
import os
import shutil
from pathlib import Path as PathLib
import uuid
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_prodigy")

# Configuration
UPLOAD_DIR = "./uploads"
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3002", "http://127.0.0.1:3002"]

# Create upload directory
upload_path = PathLib(UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)

# Create FastAPI instance
app = FastAPI(
    title="PDF Prodigy API",
    version="1.0.0",
    description="A simple PDF processing service for basic integration",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FileInfo(BaseModel):
    filename: str = Field(..., description="Sanitized filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    file_id: str = Field(..., description="Unique file identifier")
    file_url: str = Field(..., description="URL to access the file")

class UploadResponse(BaseModel):
    success: bool = Field(..., description="Upload operation success status")
    message: str = Field(..., description="Upload operation message")
    files: List[FileInfo] = Field(..., description="List of uploaded file information")

# Utility functions
def validate_file_extension(filename: str) -> bool:
    """Validate if file has a supported extension"""
    if not filename:
        return False
    extension = PathLib(filename).suffix.lower()
    return extension == '.pdf'

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unnamed_file.pdf"
    
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    if not filename.endswith('.pdf'):
        filename += '.pdf'
    
    return filename

# API Routes
@app.get("/")
async def root():
    return {
        "message": "PDF Prodigy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": "PDF Prodigy API",
        "version": "1.0.0"
    }

@app.post("/api/v1/files/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="List of PDF files to upload")
):
    """Upload PDF files for processing"""
    try:
        uploaded_files = []
        upload_dir = PathLib(UPLOAD_DIR)
        
        for file in files:
            # Validate file extension
            if not validate_file_extension(file.filename):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {file.filename}. Only PDF files are supported."
                )
            
            # Generate unique file ID and sanitize filename
            file_id = str(uuid.uuid4())
            sanitized_filename = sanitize_filename(file.filename)
            file_path = upload_dir / f"{file_id}_{sanitized_filename}"
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            file_info = FileInfo(
                filename=sanitized_filename,
                size=file_size,
                mime_type=file.content_type or "application/pdf",
                file_id=file_id,
                file_url=f"http://localhost:8000/api/v1/files/{file_id}/view"
            )
            uploaded_files.append(file_info)
            
            logger.info(f"Uploaded file: {sanitized_filename} with ID: {file_id}")
        
        return UploadResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} file(s)",
            files=uploaded_files
        )
        
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@app.get("/api/v1/files/validate/{filename}")
async def validate_file(filename: str = Path(..., description="Filename to validate")):
    """Validate file format before upload"""
    try:
        is_valid = validate_file_extension(filename)
        
        return {
            "filename": filename,
            "is_valid": is_valid,
            "supported_formats": [".pdf"],
            "message": "File is valid" if is_valid else "Unsupported file format"
        }
        
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File validation failed"
        )

@app.get("/api/v1/files/{file_id}/download")
async def download_file(file_id: str = Path(..., description="File ID to download")):
    """Download a file by its ID (simulates S3-like file serving)"""
    try:
        upload_dir = PathLib(UPLOAD_DIR)
        
        # Find the file with the given ID
        file_pattern = f"{file_id}_*"
        matching_files = list(upload_dir.glob(file_pattern))
        
        if not matching_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found"
            )
        
        file_path = matching_files[0]
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Extract original filename from the stored filename
        stored_filename = file_path.name
        original_filename = stored_filename.replace(f"{file_id}_", "", 1)
        
        return FileResponse(
            path=str(file_path),
            filename=original_filename,
            media_type="application/pdf",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "no-cache",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File download failed"
        )

@app.get("/api/v1/files/{file_id}/view")
async def view_file(file_id: str = Path(..., description="File ID to view")):
    """View a file by its ID with proper headers for PDF.js"""
    try:
        upload_dir = PathLib(UPLOAD_DIR)
        
        # Find the file with the given ID
        file_pattern = f"{file_id}_*"
        matching_files = list(upload_dir.glob(file_pattern))
        
        if not matching_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found"
            )
        
        file_path = matching_files[0]
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Content-Range, Content-Length",
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": "inline",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File view error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File view failed"
        )

if __name__ == "__main__":
    logger.info("Starting PDF Prodigy API...")
    uvicorn.run(
        "standalone_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
