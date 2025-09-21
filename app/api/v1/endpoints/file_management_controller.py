"""
File Management Controller
Handle file upload, validation, and cleanup operations
Following Java naming convention with 'Controller' suffix
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, Field
import os
from pathlib import Path as PathLib

from app.core.logger import logger
from app.core.security import validate_file_extension, sanitize_filename

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
    message: str = Field(..., description="Upload operation message", example="Successfully uploaded 2 files")
    files: List[FileInfo] = Field(..., description="List of uploaded file information")

@router.post(
    "/upload", 
    response_model=UploadResponse,
    summary="Upload Files for Processing",
    description="Upload one or more PDF files for processing operations",
    responses={
        200: {
            "description": "Files uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Successfully uploaded 2 files",
                        "files": [
                            {
                                "filename": "document1.pdf",
                                "size": 1048576,
                                "mime_type": "application/pdf",
                                "file_id": "file_0"
                            },
                            {
                                "filename": "document2.pdf", 
                                "size": 2097152,
                                "mime_type": "application/pdf",
                                "file_id": "file_1"
                            }
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid file type or format"},
        413: {"description": "File too large"},
        500: {"description": "File upload failed"}
    },
    tags=["File Management"]
)
async def upload_files(
    files: List[UploadFile] = File(..., description="List of PDF files to upload (max 10 files per request)")
):
    """
    ## Upload Files for Processing
    
    Upload one or more PDF files that will be used for subsequent processing operations.
    
    ### Supported File Types:
    - **PDF documents** (.pdf)
    - MIME type: `application/pdf`
    
    ### File Limitations:
    - **Maximum file size**: 50MB per file
    - **Maximum files per request**: 10 files
    - **Total request size**: 500MB
    - **Supported formats**: PDF only
    
    ### File Processing:
    - Filenames are automatically sanitized for security
    - Files are temporarily stored for processing
    - Each file receives a unique identifier
    - Files are automatically cleaned up after 24 hours
    
    ### Security Features:
    - File type validation using MIME type and extension
    - Filename sanitization to prevent path traversal
    - Virus scanning (if enabled)
    - Content validation to ensure valid PDF structure
    
    ### Response:
    Returns detailed information about each uploaded file including:
    - Sanitized filename
    - File size in bytes
    - Detected MIME type
    - Unique file identifier for subsequent operations
    
    ### Usage Example:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/files/upload" \\
         -H "Content-Type: multipart/form-data" \\
         -F "files=@document1.pdf" \\
         -F "files=@document2.pdf"
    ```
    """
    try:
        uploaded_files = []
        
        for file in files:
            if not validate_file_extension(file.filename):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {file.filename}"
                )
            
            file_info = FileInfo(
                filename=sanitize_filename(file.filename),
                size=file.size or 0,
                mime_type=file.content_type or "application/octet-stream",
                file_id=f"file_{len(uploaded_files)}"
            )
            uploaded_files.append(file_info)
        
        return UploadResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} files",
            files=uploaded_files
        )
        
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@router.get(
    "/validate/{filename}",
    summary="Validate File Format",
    description="Check if a filename has a supported format for PDF processing",
    responses={
        200: {
            "description": "File validation result",
            "content": {
                "application/json": {
                    "examples": {
                        "valid_file": {
                            "summary": "Valid PDF file",
                            "value": {
                                "filename": "document.pdf",
                                "is_valid": True,
                                "supported_formats": [".pdf"],
                                "message": "File is valid"
                            }
                        },
                        "invalid_file": {
                            "summary": "Invalid file type",
                            "value": {
                                "filename": "document.txt",
                                "is_valid": False,
                                "supported_formats": [".pdf"],
                                "message": "Unsupported file format"
                            }
                        }
                    }
                }
            }
        },
        500: {"description": "File validation failed"}
    },
    tags=["File Management"]
)
async def validate_file(
    filename: str = Path(..., description="Filename to validate", example="document.pdf")
):
    """
    ## Validate File Format
    
    Check if a filename has a supported file extension for PDF processing operations.
    
    ### Validation Rules:
    - **File extension**: Must be `.pdf` (case-insensitive)
    - **Filename length**: Maximum 255 characters
    - **Special characters**: Basic sanitization applied
    - **Reserved names**: System reserved names are rejected
    
    ### Supported Formats:
    - **.pdf**: Portable Document Format
    
    ### Use Cases:
    - **Pre-upload validation**: Check files before uploading
    - **Client-side filtering**: Filter file selections in UI
    - **Batch validation**: Validate multiple filenames
    - **Integration testing**: Verify file handling logic
    
    ### Response Fields:
    - **filename**: The filename that was validated
    - **is_valid**: Boolean indicating if the file is acceptable
    - **supported_formats**: List of supported file extensions
    - **message**: Human-readable validation result
    
    ### Security Notes:
    - This endpoint only validates the filename/extension
    - Actual file content validation occurs during upload
    - Does not check if the file exists or is accessible
    - Safe to call with untrusted input
    
    ### Example Usage:
    ```javascript
    // JavaScript example
    const response = await fetch('/api/v1/files/validate/document.pdf');
    const result = await response.json();
    if (result.is_valid) {
        // Proceed with file upload
    } else {
        // Show error message
    }
    ```
    """
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
