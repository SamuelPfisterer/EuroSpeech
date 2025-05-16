from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
import re

class TranscriptPreprocessor(ABC):
    """Base interface for transcript preprocessing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, abbreviations: Optional[Dict[str, str]] = None):
        """Initialize with optional configuration parameters.
        
        Args:
            config: Dictionary of configuration parameters
            abbreviations: Dictionary mapping abbreviations to their full forms
        """
        self.config = config or {}
        self.abbreviations = abbreviations or {}
    
    @classmethod
    @abstractmethod
    def can_process(cls, file_path: str) -> bool:
        """Check if this preprocessor can handle the given file.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            True if this preprocessor can handle the file, False otherwise
        """
        pass
    
    @abstractmethod
    def preprocess(self, file_path: str) -> str:
        """Preprocess the transcript file and return the cleaned text.
        
        Args:
            file_path: Path to the transcript file
            
        Returns:
            Preprocessed transcript text as a string
        """
        pass
    
    def solve_abbreviations(self, text: str) -> str:
        """Replace abbreviations in the text with their full forms.
        
        Args:
            text: Input text with potential abbreviations
            
        Returns:
            Text with abbreviations replaced by their full forms
        """
        if not self.abbreviations:
            return text
            
        result = text
        
        for abbr, full_form in self.abbreviations.items():
            # Create a pattern that matches the abbreviation as a whole word
            pattern = r'\b' + re.escape(abbr) + r'\b'
            # Replace all occurrences with the full form
            result = re.sub(pattern, full_form, result)
                
        return result
