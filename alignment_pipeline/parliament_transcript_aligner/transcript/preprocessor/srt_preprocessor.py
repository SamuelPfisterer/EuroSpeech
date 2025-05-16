from pathlib import Path
from .base import TranscriptPreprocessor

class SrtPreprocessor(TranscriptPreprocessor):
    """Preprocessor for SRT subtitle files."""
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """Check if the file is an SRT file.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            True if the file has a .srt extension
        """
        return Path(file_path).suffix.lower() == '.srt'
    
    def preprocess(self, file_path: str) -> str:
        """Preprocess an SRT subtitle file.
        
        Extracts only the subtitle text and concatenates it, ignoring
        timecodes, subtitle numbers, and other metadata.
        
        Args:
            file_path: Path to the subtitle file
            
        Returns:
            Concatenated subtitle text
        """
        try:
            import pysrt
        except ImportError:
            raise ImportError("Please install pysrt for SRT processing: pip install pysrt")
        
        # Parse the SRT file using pysrt
        subs = pysrt.open(file_path)
        
        # Extract only the text content from each subtitle
        subtitle_texts = [sub.text for sub in subs]
        
        # Join all subtitle texts with spaces
        full_text = ' '.join(subtitle_texts)
        
        # Remove HTML tags if present (common in SRT files)
        if self.config.get('remove_html_tags', True):
            import re
            full_text = re.sub(r'<[^>]+>', '', full_text)
        
        # Apply additional processing based on configuration
        if self.config.get('normalize_whitespace', True):
            full_text = ' '.join(full_text.split())
        
        return full_text
