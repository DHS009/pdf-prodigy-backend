"""
Simplified security functions for basic integration
"""

import os
import re
from pathlib import Path

def validate_file_extension(filename: str) -> bool:
    """Validate if file has a supported extension"""
    if not filename:
        return False
    
    extension = Path(filename).suffix.lower()
    return extension == '.pdf'

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unnamed_file.pdf"
    
    # Remove directory path
    filename = os.path.basename(filename)
    
    # Replace unsafe characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure it has a valid extension
    if not filename.endswith('.pdf'):
        filename += '.pdf'
    
    return filename
