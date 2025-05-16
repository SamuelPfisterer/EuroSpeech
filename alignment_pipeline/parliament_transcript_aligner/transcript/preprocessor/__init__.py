from typing import Dict, Any, Optional
from pathlib import Path

from .base import TranscriptPreprocessor
from .txt_preprocessor import TxtPreprocessor
from .pdf_preprocessor import PdfPreprocessor
from .srt_preprocessor import SrtPreprocessor
from .docx_preprocessor import DocxPreprocessor
from .html_preprocessor import HtmlPreprocessor
def create_preprocessor(file_path: str, config: Optional[Dict[str, Any]] = None) -> TranscriptPreprocessor:
    """Create appropriate preprocessor for the given file.
    
    Args:
        file_path: Path to the transcript file
        config: Optional configuration parameters
        
    Returns:
        An appropriate preprocessor instance
        
    Raises:
        ValueError: If no suitable preprocessor is found
    """
    preprocessors = [TxtPreprocessor, PdfPreprocessor, SrtPreprocessor, DocxPreprocessor, HtmlPreprocessor]
    
    for preprocessor_class in preprocessors:
        if preprocessor_class.can_process(file_path):
            return preprocessor_class(config)
            
    raise ValueError(f"No suitable preprocessor found for {file_path}")
# Export the classes and factory function
__all__ = ['TranscriptPreprocessor', 'TxtPreprocessor', 'PdfPreprocessor', 'SrtPreprocessor', 'DocxPreprocessor', 'HtmlPreprocessor', 'create_preprocessor']

