from pathlib import Path
from .base import TranscriptPreprocessor

class HtmlPreprocessor(TranscriptPreprocessor):
    """Preprocessor for HTML transcript files.
    
    This preprocessor allows for flexible HTML processing through a configurable
    processor function. Users can provide their own HTML processor via the config
    parameter when initializing the preprocessor.
    
    To use a custom processor:
    1. Define a function that takes html_content (str) and config (dict) as parameters
    2. Return the extracted text as a string
    3. Pass the function via config['html_processor'] when creating the preprocessor
    
    Example:
        def my_custom_processor(html_content, config):
            # Custom HTML processing logic
            return extracted_text
            
        preprocessor = HtmlPreprocessor(config={'html_processor': my_custom_processor})
    """
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in ['.html', '.htm']
    
    def preprocess(self, file_path: str) -> str:
        # Get the HTML processor from config or use default
        # The processor must be a callable that accepts (html_content: str, config: dict)
        # and returns the extracted text as a string
        processor = self.config.get('html_processor', self._default_processor)

        if processor == self._default_processor:
            print(f"Using default HTML processor")
        else:
            print(f"Using custom HTML processor")
        
        # Load HTML content
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Process using the provided processor
        text = processor(html_content, self.config)
        
        return self.solve_abbreviations(text)
        
    def _default_processor(self, html_content: str, config: dict) -> str:
        """Default HTML processing method.
        
        Args:
            html_content: Raw HTML content as string
            config: Configuration dictionary that may contain processing options
            
        Returns:
            Extracted text content from the HTML
            
        Note:
            Custom processors should follow this same signature.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("Please install BeautifulSoup: pip install beautifulsoup4")
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text from body
        return soup.get_text(separator=' ')
