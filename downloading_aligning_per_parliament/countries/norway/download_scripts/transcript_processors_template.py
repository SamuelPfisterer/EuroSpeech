from typing import Union, Tuple

def process_transcript(url: str) -> Tuple[Union[str, bytes], str]:
    """
    Process transcript URL and return content with its type.
    
    Args:
        url: The URL to process
        
    Returns:
        Tuple[Union[str, bytes], str]: (content, type) where:
        - content is either the processed content or a URL
        - type is one of: 'pdf_link', 'html_content', 'text_content'
        
    Example returns:
        - ("http://example.com/doc.pdf", "pdf_link")
        - ("<html>...</html>", "html_content")
        - ("Plain text...", "text_content")
        
    Raises:
        ValueError: If processing fails
        Any other exceptions that occur during processing
    """
    try:
        # Your processing logic here
        # Example 1: Return PDF link
        # return "http://example.com/doc.pdf", "pdf_link"
        
        # Example 2: Return processed HTML
        # return "<html><body>Processed content</body></html>", "html_content"
        
        # Example 3: Return processed text
        # return "Plain text content", "text_content"
        
        raise NotImplementedError("Please implement your transcript processing logic")
        
    except Exception as e:
        raise ValueError(f"Failed to process transcript: {str(e)}") 