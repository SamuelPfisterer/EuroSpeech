from pathlib import Path
from .base import TranscriptPreprocessor

class TxtPreprocessor(TranscriptPreprocessor):
    """Preprocessor for plain text transcript files."""
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """Check if the file is a text file.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            True if the file has a .txt extension
        """
        return Path(file_path).suffix.lower() == '.txt'
    
    def preprocess(self, file_path: str) -> str:
        """Preprocess a plain text transcript file.
        
        For text files, preprocessing is minimal - just read the file and 
        perform basic cleaning like stripping whitespace.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            Preprocessed transcript text
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Apply basic cleaning
        text = text.strip()
        
        # Apply additional processing based on configuration
        if self.config.get('normalize_whitespace', True):
            text = ' '.join(text.split())
        
        return text
