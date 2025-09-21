"""
PDF Operations Controller
Core PDF editing, splitting, and merging operations
Following Java naming convention with 'Controller' suffix
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import tempfile
import os
from pathlib import Path

from app.core.logger import logger
from app.services.pdf_service import PDFService
from app.core.security import generate_session_id, sanitize_filename, validate_file_extension

router = APIRouter()

# ========================
# REQUEST/RESPONSE MODELS
# ========================

class PDFEditRequest(BaseModel):
    """Request model for PDF editing operations"""
    operation_type: str  # "add_text", "add_image", "add_annotation", "remove_element"
    page_number: int
    data: Dict[str, Any]  # Operation-specific data
    
class TextElement(BaseModel):
    """Text element for PDF editing"""
    text: str
    x: float
    y: float
    font_size: int = 12
    font_family: str = "Arial"
    color: str = "#000000"
    rotation: float = 0.0

class ImageElement(BaseModel):
    """Image element for PDF editing"""
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: float = 0.0

class SplitRequest(BaseModel):
    """Request model for PDF splitting"""
    split_type: str  # "pages", "range", "bookmark", "size"
    pages: Optional[List[int]] = None  # Specific pages to extract
    page_ranges: Optional[List[str]] = None  # e.g., ["1-5", "8-10"]
    max_pages_per_file: Optional[int] = None  # For size-based splitting

class MergeRequest(BaseModel):
    """Request model for PDF merging"""
    merge_order: List[int]  # Order of files to merge
    bookmark_structure: Optional[bool] = True  # Preserve bookmarks
    page_numbering: Optional[bool] = True  # Add page numbers

class OperationResponse(BaseModel):
    """Standard response model for all operations"""
    success: bool
    message: str
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# ========================
# PDF EDIT ENDPOINT
# ========================

@router.post(
    "/edit", 
    response_model=OperationResponse,
    summary="Edit PDF Document",
    description="Add text, images, or annotations to a PDF document at specified coordinates",
    responses={
        200: {
            "description": "PDF editing completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "PDF add_text completed successfully",
                        "file_id": "abc123def456",
                        "download_url": "/api/v1/download/abc123def456",
                        "processing_time": 2.45,
                        "metadata": {
                            "operation": "add_text",
                            "page": 1,
                            "file_size": 245760
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid file type or missing parameters"},
        500: {"description": "PDF editing failed"}
    },
    tags=["PDF Operations"]
)
async def edit_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to edit"),
    operation_type: str = Form(..., description="Type of operation", example="add_text", enum=["add_text", "add_image", "add_annotation"]),
    page_number: int = Form(..., description="Page number to edit (1-indexed)", example=1, ge=1),
    # Text editing parameters
    text: Optional[str] = Form(None, description="Text to add (required for add_text)", example="Hello World"),
    x: Optional[float] = Form(None, description="X coordinate (required for text/image)", example=100.0),
    y: Optional[float] = Form(None, description="Y coordinate (required for text/image)", example=200.0),
    font_size: Optional[int] = Form(12, description="Font size for text", example=14, ge=6, le=72),
    font_family: Optional[str] = Form("Arial", description="Font family for text", example="Helvetica"),
    color: Optional[str] = Form("#000000", description="Text color in hex format", example="#FF0000"),
    # Image editing parameters
    image_file: Optional[UploadFile] = File(None, description="Image file to add (required for add_image)"),
    width: Optional[float] = Form(None, description="Image width in points", example=150.0),
    height: Optional[float] = Form(None, description="Image height in points", example=100.0),
    rotation: Optional[float] = Form(0.0, description="Rotation angle in degrees", example=45.0, ge=-360, le=360)
):
    """
    ## Edit PDF Document
    
    Add various elements to a PDF document at specified coordinates.
    
    ### Supported Operations:
    - **add_text**: Add text at specified coordinates
      - Required: `text`, `x`, `y`
      - Optional: `font_size`, `font_family`, `color`, `rotation`
    
    - **add_image**: Insert image at specified position
      - Required: `image_file`, `x`, `y`
      - Optional: `width`, `height`, `rotation`
    
    - **add_annotation**: Add highlight, note, or drawing
      - Required: `x`, `y`
      - Optional: `width`, `height`, `color`
    
    ### Coordinate System:
    - Origin (0,0) is at bottom-left corner
    - X increases to the right
    - Y increases upward
    - Units are in points (1 point = 1/72 inch)
    
    ### Response:
    Returns a file ID that can be used to download the edited PDF.
    """
    
    try:
        # Validate file
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only PDF files are allowed."
            )
        
        logger.info(f"Starting PDF edit operation: {operation_type} on page {page_number}")
        
        # Generate session ID for tracking
        session_id = generate_session_id()
        
        # Save uploaded file temporarily
        temp_dir = Path(tempfile.gettempdir()) / "pdf_editor" / session_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        input_file = temp_dir / sanitize_filename(file.filename)
        with open(input_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Prepare operation data
        operation_data = {
            "operation_type": operation_type,
            "page_number": page_number,
            "session_id": session_id
        }
        
        if operation_type == "add_text":
            if not all([text, x is not None, y is not None]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required text parameters: text, x, y"
                )
            operation_data.update({
                "text": text,
                "x": x,
                "y": y,
                "font_size": font_size,
                "font_family": font_family,
                "color": color,
                "rotation": rotation
            })
            
        elif operation_type == "add_image":
            if not image_file or not all([x is not None, y is not None]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required image parameters: image_file, x, y"
                )
            
            # Save image file
            image_path = temp_dir / sanitize_filename(image_file.filename)
            with open(image_path, "wb") as buffer:
                image_content = await image_file.read()
                buffer.write(image_content)
            
            operation_data.update({
                "image_path": str(image_path),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": rotation
            })
        
        # Initialize PDF service
        pdf_service = PDFService()
        
        # Process PDF editing
        result = await pdf_service.edit_pdf(
            input_file=str(input_file),
            operation_data=operation_data
        )
        
        if result["success"]:
            return OperationResponse(
                success=True,
                message=f"PDF {operation_type} completed successfully",
                file_id=result["file_id"],
                download_url=f"/api/v1/download/{result['file_id']}",
                processing_time=result.get("processing_time"),
                metadata=result.get("metadata")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "PDF editing failed")
            )
            
    except Exception as e:
        logger.error(f"PDF edit error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF editing failed: {str(e)}"
        )

# ========================
# PDF SPLIT ENDPOINT
# ========================

@router.post(
    "/split", 
    response_model=OperationResponse,
    summary="Split PDF Document",
    description="Split a PDF document into multiple files using various splitting strategies",
    responses={
        200: {
            "description": "PDF splitting completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "PDF split into 3 files",
                        "file_id": "xyz789abc123",
                        "download_url": "/api/v1/download/xyz789abc123",
                        "processing_time": 1.23,
                        "metadata": {
                            "file_count": 3,
                            "split_type": "pages",
                            "output_files": ["page_1.pdf", "page_3.pdf", "page_5.pdf"]
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid file type or parameters"},
        500: {"description": "PDF splitting failed"}
    },
    tags=["PDF Operations"]
)
async def split_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to split"),
    split_type: str = Form(..., description="Method to split the PDF", example="pages", enum=["pages", "range", "bookmark", "size"]),
    pages: Optional[str] = Form(None, description="Comma-separated page numbers (for 'pages' type)", example="1,3,5"),
    page_ranges: Optional[str] = Form(None, description="Comma-separated page ranges (for 'range' type)", example="1-5,8-10"),
    max_pages_per_file: Optional[int] = Form(None, description="Maximum pages per output file (for 'size' type)", example=10, ge=1)
):
    """
    ## Split PDF Document
    
    Split a PDF document into multiple files using different strategies.
    
    ### Split Types:
    
    #### 1. **pages** - Extract specific pages
    - Parameter: `pages` (comma-separated page numbers)
    - Example: `pages="1,3,5"` extracts pages 1, 3, and 5
    - Output: Separate PDF file for each specified page
    
    #### 2. **range** - Extract page ranges
    - Parameter: `page_ranges` (comma-separated ranges)
    - Example: `page_ranges="1-5,8-10"` extracts pages 1-5 and 8-10
    - Output: Separate PDF file for each range
    
    #### 3. **size** - Split by maximum pages per file
    - Parameter: `max_pages_per_file` (integer)
    - Example: `max_pages_per_file=10` creates files with max 10 pages each
    - Output: Multiple PDF files with specified page limit
    
    #### 4. **bookmark** - Split by bookmarks/sections
    - No additional parameters required
    - Splits at each top-level bookmark
    - Output: Separate PDF file for each bookmark section
    
    ### Page Numbering:
    - Pages are numbered starting from 1
    - Invalid page numbers are ignored
    - Ranges use format "start-end" (inclusive)
    
    ### Response:
    Returns a file ID that can be used to download a ZIP file containing all split PDFs.
    """
    
    try:
        # Validate file
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only PDF files are allowed."
            )
        
        logger.info(f"Starting PDF split operation: {split_type}")
        
        # Generate session ID
        session_id = generate_session_id()
        
        # Save uploaded file
        temp_dir = Path(tempfile.gettempdir()) / "pdf_editor" / session_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        input_file = temp_dir / sanitize_filename(file.filename)
        with open(input_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse split parameters
        split_config = {
            "split_type": split_type,
            "session_id": session_id
        }
        
        if split_type == "pages" and pages:
            split_config["pages"] = [int(p.strip()) for p in pages.split(",")]
        elif split_type == "range" and page_ranges:
            split_config["page_ranges"] = [r.strip() for r in page_ranges.split(",")]
        elif split_type == "size" and max_pages_per_file:
            split_config["max_pages_per_file"] = max_pages_per_file
        
        # Initialize PDF service
        pdf_service = PDFService()
        
        # Process PDF splitting
        result = await pdf_service.split_pdf(
            input_file=str(input_file),
            split_config=split_config
        )
        
        if result["success"]:
            return OperationResponse(
                success=True,
                message=f"PDF split into {result['file_count']} files",
                file_id=result["file_id"],
                download_url=f"/api/v1/download/{result['file_id']}",
                processing_time=result.get("processing_time"),
                metadata={
                    "file_count": result["file_count"],
                    "split_type": split_type,
                    "output_files": result.get("output_files", [])
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "PDF splitting failed")
            )
            
    except Exception as e:
        logger.error(f"PDF split error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF splitting failed: {str(e)}"
        )

# ========================
# PDF MERGE ENDPOINT
# ========================

@router.post(
    "/merge", 
    response_model=OperationResponse,
    summary="Merge PDF Documents",
    description="Combine multiple PDF files into a single document with optional features",
    responses={
        200: {
            "description": "PDF merging completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Successfully merged 3 PDF files",
                        "file_id": "merge456def789",
                        "download_url": "/api/v1/download/merge456def789",
                        "processing_time": 3.67,
                        "metadata": {
                            "merged_files": 3,
                            "total_pages": 25,
                            "bookmark_structure": True,
                            "page_numbering": True
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid files or insufficient files for merging"},
        500: {"description": "PDF merging failed"}
    },
    tags=["PDF Operations"]
)
async def merge_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="List of PDF files to merge (minimum 2 files)"),
    merge_order: Optional[str] = Form(None, description="Custom order for merging files (comma-separated indices)", example="0,2,1"),
    bookmark_structure: bool = Form(True, description="Preserve and organize bookmark structure"),
    page_numbering: bool = Form(True, description="Add page numbers to the merged document")
):
    """
    ## Merge PDF Documents
    
    Combine multiple PDF files into a single document with advanced options.
    
    ### Features:
    
    #### File Order
    - **Default**: Files are merged in upload order
    - **Custom Order**: Use `merge_order` parameter
      - Example: `merge_order="0,2,1"` merges files in order: 1st, 3rd, 2nd
      - Indices are 0-based (0 = first file, 1 = second file, etc.)
    
    #### Bookmark Structure
    - **Enabled** (default): Creates bookmarks for each merged document
    - **Disabled**: Simple concatenation without bookmarks
    - Preserves existing bookmarks from source documents
    
    #### Page Numbering
    - **Enabled** (default): Adds sequential page numbers
    - **Disabled**: No page numbering added
    - Numbers appear at bottom center of each page
    
    ### Requirements:
    - Minimum 2 PDF files required
    - All files must be valid PDF documents
    - Maximum recommended: 50 files per merge operation
    - Total size limit: 500MB per operation
    
    ### Output:
    Single PDF file containing all merged content with optional enhancements.
    
    ### Performance Notes:
    - Large files may take longer to process
    - Use background processing for files >100MB
    - Progress can be tracked using the status endpoint
    """
    
    try:
        # Validate files
        if len(files) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 PDF files are required for merging"
            )
        
        for file in files:
            if not validate_file_extension(file.filename):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {file.filename}. Only PDF files are allowed."
                )
        
        logger.info(f"Starting PDF merge operation with {len(files)} files")
        
        # Generate session ID
        session_id = generate_session_id()
        
        # Save uploaded files
        temp_dir = Path(tempfile.gettempdir()) / "pdf_editor" / session_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        input_files = []
        for i, file in enumerate(files):
            file_path = temp_dir / f"{i}_{sanitize_filename(file.filename)}"
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            input_files.append(str(file_path))
        
        # Parse merge order
        if merge_order:
            order_indices = [int(idx.strip()) for idx in merge_order.split(",")]
            if len(order_indices) != len(files):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Merge order must specify all files"
                )
            # Reorder files according to specified order
            input_files = [input_files[i] for i in order_indices]
        
        merge_config = {
            "session_id": session_id,
            "bookmark_structure": bookmark_structure,
            "page_numbering": page_numbering,
            "file_count": len(files)
        }
        
        # Initialize PDF service
        pdf_service = PDFService()
        
        # Process PDF merging
        result = await pdf_service.merge_pdfs(
            input_files=input_files,
            merge_config=merge_config
        )
        
        if result["success"]:
            return OperationResponse(
                success=True,
                message=f"Successfully merged {len(files)} PDF files",
                file_id=result["file_id"],
                download_url=f"/api/v1/download/{result['file_id']}",
                processing_time=result.get("processing_time"),
                metadata={
                    "merged_files": len(files),
                    "total_pages": result.get("total_pages"),
                    "bookmark_structure": bookmark_structure,
                    "page_numbering": page_numbering
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "PDF merging failed")
            )
            
    except Exception as e:
        logger.error(f"PDF merge error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF merging failed: {str(e)}"
        )

# ========================
# UTILITY ENDPOINTS
# ========================

@router.get(
    "/download/{file_id}",
    summary="Download Processed File",
    description="Download the processed PDF file using the file ID from previous operations",
    responses={
        200: {
            "description": "File download successful",
            "content": {"application/pdf": {}},
            "headers": {
                "Content-Disposition": {
                    "description": "Attachment filename",
                    "schema": {"type": "string", "example": "attachment; filename=processed_abc123.pdf"}
                }
            }
        },
        404: {"description": "File not found or expired"},
        500: {"description": "File download failed"}
    },
    tags=["Utility Operations"]
)
async def download_file(
    file_id: str = Path(..., description="Unique file identifier from processing operation", example="abc123def456")
):
    """
    ## Download Processed File
    
    Download the result of a PDF processing operation using the file ID.
    
    ### Usage:
    1. Perform a PDF operation (edit, split, merge)
    2. Get the `file_id` from the operation response
    3. Use this endpoint to download the processed file
    
    ### File Availability:
    - Files are available for **24 hours** after processing
    - Files are automatically cleaned up after expiration
    - Use the status endpoint to check file availability
    
    ### Response:
    - Content-Type: `application/pdf`
    - Content-Disposition: `attachment; filename="processed_{file_id}.pdf"`
    - Binary PDF data for direct download
    
    ### Error Cases:
    - **404**: File not found, expired, or invalid file_id
    - **500**: Server error during file retrieval
    """
    try:
        # Implement file download logic
        pdf_service = PDFService()
        file_path = await pdf_service.get_file_path(file_id)
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=f"processed_{file_id}.pdf"
        )
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File download failed"
        )

@router.get(
    "/status/{file_id}",
    summary="Check Processing Status",
    description="Get the current status and progress of an async PDF processing operation",
    responses={
        200: {
            "description": "Status check successful",
            "content": {
                "application/json": {
                    "example": {
                        "file_id": "abc123def456",
                        "status": "completed",
                        "progress": 100,
                        "message": "Processing completed successfully",
                        "created_at": 1695123456.789,
                        "completed_at": 1695123459.234
                    }
                }
            }
        },
        404: {"description": "File ID not found"},
        500: {"description": "Status check failed"}
    },
    tags=["Utility Operations"]
)
async def get_processing_status(
    file_id: str = Path(..., description="Unique file identifier from processing operation", example="abc123def456")
):
    """
    ## Check Processing Status
    
    Monitor the progress of PDF processing operations, especially useful for large files.
    
    ### Status Values:
    - **pending**: Operation queued but not started
    - **processing**: Currently being processed
    - **completed**: Successfully finished
    - **failed**: Processing encountered an error
    - **not_found**: File ID doesn't exist
    
    ### Progress Values:
    - **0-99**: Processing in progress (percentage)
    - **100**: Completed successfully
    - **-1**: Error occurred during processing
    
    ### Timestamps:
    - **created_at**: When the operation was initiated (Unix timestamp)
    - **completed_at**: When processing finished (Unix timestamp, null if not completed)
    
    ### Use Cases:
    - Poll this endpoint for long-running operations
    - Display progress bars in frontend applications
    - Implement retry logic for failed operations
    - Check if files are ready for download
    
    ### Polling Recommendations:
    - Small files (< 10MB): Check every 1-2 seconds
    - Large files (> 10MB): Check every 5-10 seconds
    - Stop polling when status is 'completed' or 'failed'
    """
    try:
        pdf_service = PDFService()
        status_info = await pdf_service.get_processing_status(file_id)
        
        return {
            "file_id": file_id,
            "status": status_info.get("status", "unknown"),
            "progress": status_info.get("progress", 0),
            "message": status_info.get("message", ""),
            "created_at": status_info.get("created_at"),
            "completed_at": status_info.get("completed_at")
        }
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status check failed"
        )
