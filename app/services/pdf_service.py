"""
PDF Service for processing PDF operations
Handles editing, splitting, and merging of PDF files
"""

import os
import time
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import PyPDF2
from io import BytesIO

from app.core.logger import logger
from app.core.security import generate_session_id


class PDFService:
    """Service class for PDF operations"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "pdf_editor"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def edit_pdf(self, input_file: str, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit PDF by adding text, images, or annotations
        """
        start_time = time.time()
        session_id = operation_data.get("session_id", generate_session_id())
        
        try:
            logger.info(f"Starting PDF edit operation: {operation_data['operation_type']}")
            
            # Open PDF with PyMuPDF for editing
            doc = fitz.open(input_file)
            
            if operation_data["page_number"] > len(doc):
                raise ValueError(f"Page {operation_data['page_number']} does not exist")
            
            page = doc.load_page(operation_data["page_number"] - 1)  # 0-indexed
            
            if operation_data["operation_type"] == "add_text":
                await self._add_text_to_page(page, operation_data)
            elif operation_data["operation_type"] == "add_image":
                await self._add_image_to_page(page, operation_data)
            elif operation_data["operation_type"] == "add_annotation":
                await self._add_annotation_to_page(page, operation_data)
            else:
                raise ValueError(f"Unsupported operation: {operation_data['operation_type']}")
            
            # Save the modified PDF
            output_file = self.temp_dir / session_id / f"edited_{int(time.time())}.pdf"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            doc.save(str(output_file))
            doc.close()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "file_id": session_id,
                "output_file": str(output_file),
                "processing_time": processing_time,
                "metadata": {
                    "operation": operation_data["operation_type"],
                    "page": operation_data["page_number"],
                    "file_size": output_file.stat().st_size
                }
            }
            
        except Exception as e:
            logger.error(f"PDF edit error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _add_text_to_page(self, page, data: Dict[str, Any]):
        """Add text to PDF page"""
        try:
            # Create a text rectangle
            rect = fitz.Rect(
                data["x"], 
                data["y"], 
                data["x"] + len(data["text"]) * data["font_size"] * 0.6,  # Approximate width
                data["y"] + data["font_size"]
            )
            
            # Add text
            page.insert_text(
                point=(data["x"], data["y"]),
                text=data["text"],
                fontsize=data["font_size"],
                fontname=data.get("font_family", "helv"),  # Helvetica
                color=self._hex_to_rgb(data.get("color", "#000000")),
                rotate=data.get("rotation", 0)
            )
            
            logger.info(f"Added text '{data['text']}' at ({data['x']}, {data['y']})")
            
        except Exception as e:
            logger.error(f"Error adding text: {str(e)}")
            raise
    
    async def _add_image_to_page(self, page, data: Dict[str, Any]):
        """Add image to PDF page"""
        try:
            image_path = data["image_path"]
            
            # Open and process image
            img = Image.open(image_path)
            
            # Calculate dimensions
            width = data.get("width", img.width)
            height = data.get("height", img.height)
            
            # Create rectangle for image placement
            rect = fitz.Rect(
                data["x"], 
                data["y"], 
                data["x"] + width, 
                data["y"] + height
            )
            
            # Insert image
            page.insert_image(rect, filename=image_path, rotate=data.get("rotation", 0))
            
            logger.info(f"Added image at ({data['x']}, {data['y']}) with size {width}x{height}")
            
        except Exception as e:
            logger.error(f"Error adding image: {str(e)}")
            raise
    
    async def _add_annotation_to_page(self, page, data: Dict[str, Any]):
        """Add annotation to PDF page"""
        try:
            # Add highlight annotation (example)
            rect = fitz.Rect(
                data["x"], 
                data["y"], 
                data["x"] + data.get("width", 100), 
                data["y"] + data.get("height", 20)
            )
            
            highlight = page.add_highlight_annot(rect)
            highlight.set_colors(stroke=self._hex_to_rgb(data.get("color", "#FFFF00")))
            highlight.update()
            
            logger.info(f"Added annotation at ({data['x']}, {data['y']})")
            
        except Exception as e:
            logger.error(f"Error adding annotation: {str(e)}")
            raise
    
    async def split_pdf(self, input_file: str, split_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Split PDF into multiple files based on configuration
        """
        start_time = time.time()
        session_id = split_config.get("session_id", generate_session_id())
        
        try:
            logger.info(f"Starting PDF split operation: {split_config['split_type']}")
            
            # Open PDF
            doc = fitz.open(input_file)
            total_pages = len(doc)
            
            output_files = []
            output_dir = self.temp_dir / session_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if split_config["split_type"] == "pages":
                # Extract specific pages
                pages = split_config.get("pages", [])
                for i, page_num in enumerate(pages):
                    if 1 <= page_num <= total_pages:
                        new_doc = fitz.open()
                        new_doc.insert_pdf(doc, from_page=page_num-1, to_page=page_num-1)
                        
                        output_file = output_dir / f"page_{page_num}.pdf"
                        new_doc.save(str(output_file))
                        new_doc.close()
                        output_files.append(str(output_file))
            
            elif split_config["split_type"] == "range":
                # Extract page ranges
                ranges = split_config.get("page_ranges", [])
                for i, page_range in enumerate(ranges):
                    start_page, end_page = map(int, page_range.split("-"))
                    if 1 <= start_page <= end_page <= total_pages:
                        new_doc = fitz.open()
                        new_doc.insert_pdf(doc, from_page=start_page-1, to_page=end_page-1)
                        
                        output_file = output_dir / f"pages_{start_page}-{end_page}.pdf"
                        new_doc.save(str(output_file))
                        new_doc.close()
                        output_files.append(str(output_file))
            
            elif split_config["split_type"] == "size":
                # Split by maximum pages per file
                max_pages = split_config.get("max_pages_per_file", 10)
                for i in range(0, total_pages, max_pages):
                    end_page = min(i + max_pages - 1, total_pages - 1)
                    
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=i, to_page=end_page)
                    
                    output_file = output_dir / f"part_{i//max_pages + 1}.pdf"
                    new_doc.save(str(output_file))
                    new_doc.close()
                    output_files.append(str(output_file))
            
            doc.close()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "file_id": session_id,
                "file_count": len(output_files),
                "output_files": output_files,
                "processing_time": processing_time,
                "metadata": {
                    "split_type": split_config["split_type"],
                    "original_pages": total_pages,
                    "output_files": len(output_files)
                }
            }
            
        except Exception as e:
            logger.error(f"PDF split error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def merge_pdfs(self, input_files: List[str], merge_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple PDF files into one
        """
        start_time = time.time()
        session_id = merge_config.get("session_id", generate_session_id())
        
        try:
            logger.info(f"Starting PDF merge operation with {len(input_files)} files")
            
            # Create new document for merged content
            merged_doc = fitz.open()
            total_pages = 0
            
            for i, file_path in enumerate(input_files):
                doc = fitz.open(file_path)
                page_count = len(doc)
                
                # Insert all pages from current document
                merged_doc.insert_pdf(doc, from_page=0, to_page=page_count-1)
                total_pages += page_count
                
                # Add bookmark if requested
                if merge_config.get("bookmark_structure", True):
                    bookmark_title = f"Document {i+1}"
                    merged_doc.set_toc_item(
                        level=1, 
                        title=bookmark_title, 
                        page=total_pages - page_count,
                        to=fitz.Point(0, 0)
                    )
                
                doc.close()
            
            # Add page numbers if requested
            if merge_config.get("page_numbering", True):
                await self._add_page_numbers(merged_doc)
            
            # Save merged document
            output_dir = self.temp_dir / session_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"merged_{int(time.time())}.pdf"
            merged_doc.save(str(output_file))
            merged_doc.close()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "file_id": session_id,
                "output_file": str(output_file),
                "total_pages": total_pages,
                "processing_time": processing_time,
                "metadata": {
                    "merged_files": len(input_files),
                    "total_pages": total_pages,
                    "file_size": output_file.stat().st_size
                }
            }
            
        except Exception as e:
            logger.error(f"PDF merge error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _add_page_numbers(self, doc):
        """Add page numbers to merged document"""
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Add page number at bottom center
                page_rect = page.rect
                text = f"Page {page_num + 1}"
                
                page.insert_text(
                    point=(page_rect.width / 2 - 20, page_rect.height - 20),
                    text=text,
                    fontsize=10,
                    color=(0, 0, 0)
                )
            
            logger.info(f"Added page numbers to {len(doc)} pages")
            
        except Exception as e:
            logger.error(f"Error adding page numbers: {str(e)}")
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
    
    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get file path for download"""
        try:
            session_dir = self.temp_dir / file_id
            if session_dir.exists():
                # Find the most recent PDF file in the directory
                pdf_files = list(session_dir.glob("*.pdf"))
                if pdf_files:
                    # Return the most recently created file
                    latest_file = max(pdf_files, key=lambda f: f.stat().st_ctime)
                    return str(latest_file)
            return None
            
        except Exception as e:
            logger.error(f"Error getting file path: {str(e)}")
            return None
    
    async def get_processing_status(self, file_id: str) -> Dict[str, Any]:
        """Get processing status for a file"""
        try:
            session_dir = self.temp_dir / file_id
            
            if session_dir.exists():
                pdf_files = list(session_dir.glob("*.pdf"))
                if pdf_files:
                    return {
                        "status": "completed",
                        "progress": 100,
                        "message": "Processing completed successfully",
                        "created_at": session_dir.stat().st_ctime,
                        "completed_at": time.time()
                    }
                else:
                    return {
                        "status": "processing",
                        "progress": 50,
                        "message": "Processing in progress",
                        "created_at": session_dir.stat().st_ctime
                    }
            else:
                return {
                    "status": "not_found",
                    "progress": 0,
                    "message": "File not found"
                }
                
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return {
                "status": "error",
                "progress": 0,
                "message": f"Status check failed: {str(e)}"
            }
