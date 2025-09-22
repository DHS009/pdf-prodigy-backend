"""
OCR Service for extracting text from PDF files using PyMuPDF and Tesseract
"""
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import logging
from typing import List, Dict, Any, Tuple
import re

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        """Initialize OCR service with configuration"""
        # Configure Tesseract (you may need to adjust the path based on your system)
        # On macOS with Homebrew: brew install tesseract
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logger.warning(f"Tesseract not found or not configured properly: {e}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF using both native text extraction and OCR
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_data = self._process_page(page, page_num)
                pages_data.append(page_data)
            
            doc.close()
            
            # Analyze overall document structure
            total_native_text = sum(len(page['native_text']) for page in pages_data)
            total_ocr_text = sum(len(page['ocr_text']) for page in pages_data)
            
            return {
                'pages': pages_data,
                'total_pages': len(pages_data),
                'native_text_length': total_native_text,
                'ocr_text_length': total_ocr_text,
                'is_scanned_document': total_native_text < (total_ocr_text * 0.1),  # Mostly scanned if native text is minimal
                'confidence_score': self._calculate_confidence(pages_data)
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def _process_page(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """
        Process a single page with both native text extraction and OCR
        
        Args:
            page: PyMuPDF page object
            page_num: Page number
            
        Returns:
            Dictionary containing page text and metadata
        """
        # Extract native text
        native_text = page.get_text()
        
        # Get page dimensions
        rect = page.rect
        
        # Convert page to image for OCR
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
        img_data = pix.tobytes("png")
        pix = None  # Free memory
        
        # Perform OCR
        image = Image.open(io.BytesIO(img_data))
        ocr_text = ""
        ocr_confidence = 0
        
        try:
            # Get OCR text with confidence data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            ocr_text = " ".join([word for word in ocr_data['text'] if word.strip()])
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            ocr_confidence = sum(confidences) / len(confidences) if confidences else 0
            
        except Exception as e:
            logger.warning(f"OCR failed for page {page_num}: {e}")
        
        # Determine best text source
        native_text_clean = self._clean_text(native_text)
        ocr_text_clean = self._clean_text(ocr_text)
        
        # Choose best text based on content quality
        if len(native_text_clean) > 50 and self._is_readable_text(native_text_clean):
            best_text = native_text_clean
            text_source = "native"
        elif len(ocr_text_clean) > 10 and ocr_confidence > 60:
            best_text = ocr_text_clean
            text_source = "ocr"
        else:
            best_text = native_text_clean if len(native_text_clean) > len(ocr_text_clean) else ocr_text_clean
            text_source = "hybrid"
        
        return {
            'page_number': page_num + 1,
            'native_text': native_text_clean,
            'ocr_text': ocr_text_clean,
            'best_text': best_text,
            'text_source': text_source,
            'ocr_confidence': ocr_confidence,
            'dimensions': {
                'width': rect.width,
                'height': rect.height
            },
            'has_images': len(page.get_images()) > 0,
            'word_count': len(best_text.split())
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters except newlines and tabs
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        return text.strip()
    
    def _is_readable_text(self, text: str) -> bool:
        """
        Determine if text appears to be readable content
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text appears readable
        """
        if len(text) < 10:
            return False
        
        # Count alphabetic characters
        alpha_chars = sum(1 for char in text if char.isalpha())
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return False
        
        # Text should be mostly alphabetic
        alpha_ratio = alpha_chars / total_chars
        
        # Check for common English words
        words = text.lower().split()
        common_words = {'the', 'and', 'to', 'of', 'a', 'in', 'for', 'is', 'on', 'that', 'by', 'this', 'with', 'from', 'at', 'as'}
        common_word_count = sum(1 for word in words if word in common_words)
        
        return alpha_ratio > 0.5 and (len(words) < 5 or common_word_count > 0)
    
    def _calculate_confidence(self, pages_data: List[Dict[str, Any]]) -> float:
        """
        Calculate overall confidence score for text extraction
        
        Args:
            pages_data: List of page data dictionaries
            
        Returns:
            Confidence score (0-100)
        """
        if not pages_data:
            return 0
        
        total_confidence = 0
        total_weight = 0
        
        for page_data in pages_data:
            word_count = page_data['word_count']
            if word_count > 0:
                if page_data['text_source'] == 'native':
                    confidence = 95  # High confidence for native text
                elif page_data['text_source'] == 'ocr':
                    confidence = page_data['ocr_confidence']
                else:
                    confidence = 70  # Medium confidence for hybrid
                
                total_confidence += confidence * word_count
                total_weight += word_count
        
        return total_confidence / total_weight if total_weight > 0 else 0
    
    def extract_text_with_positions(self, pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract text with position information for a specific page
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number (0-indexed)
            
        Returns:
            List of text elements with position data
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # Get text with position information
            text_dict = page.get_text("dict")
            text_elements = []
            
            for block in text_dict["blocks"]:
                if block.get("type") == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():
                                bbox = span["bbox"]
                                text_elements.append({
                                    "text": span["text"],
                                    "x": bbox[0],
                                    "y": bbox[1],
                                    "width": bbox[2] - bbox[0],
                                    "height": bbox[3] - bbox[1],
                                    "font": span["font"],
                                    "size": span["size"],
                                    "flags": span["flags"]
                                })
            
            doc.close()
            return text_elements
            
        except Exception as e:
            logger.error(f"Error extracting positioned text: {e}")
            raise

# Global OCR service instance
ocr_service = OCRService()
