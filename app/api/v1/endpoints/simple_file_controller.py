"""
Simplified File Management Controller for Basic Integration
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel, Field
import os
import shutil
from pathlib import Path as PathLib
import uuid

from app.core.simple_logger import logger
from app.core.simple_security import validate_file_extension, sanitize_filename
from app.core.simple_config import settings

router = APIRouter()

class FileInfo(BaseModel):
    """File information response model"""
    filename: str = Field(..., description="Sanitized filename", example="document.pdf")
    size: int = Field(..., description="File size in bytes", example=1048576)
    mime_type: str = Field(..., description="MIME type of the file", example="application/pdf")
    file_id: str = Field(..., description="Unique file identifier", example="file_0")

class UploadResponse(BaseModel):
    """File upload response model"""
    success: bool = Field(..., description="Upload operation success status", example=True)
    message: str = Field(..., description="Upload operation message", example="Successfully uploaded 1 file")
    files: List[FileInfo] = Field(..., description="List of uploaded file information")

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="List of PDF files to upload")
):
    """Upload PDF files for processing"""
    try:
        uploaded_files = []
        upload_dir = PathLib(settings.UPLOAD_DIR)
        
        for file in files:
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
                file_id=file_id
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

@router.get("/validate/{filename}")
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
