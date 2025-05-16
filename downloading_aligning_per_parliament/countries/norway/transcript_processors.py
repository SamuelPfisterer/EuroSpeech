from playwright.sync_api import sync_playwright
import logging
from typing import Union, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_transcript(url: str) -> Tuple[Union[str, bytes], str]:
    """
    Process transcript URL and return PDF link.
    
    Args:
        url: The transcript page URL
        
    Returns:
        Tuple[str, str]: (pdf_url, type) where:
        - pdf_url is the URL to the PDF file
        - type is 'pdf_link'
        
    Raises:
        ValueError: If PDF link extraction fails
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Navigate to the transcript page
            page.goto(url)
            
            # Try both possible locations for the PDF link
            pdf_link = page.evaluate('''() => {
                // First try the minutes-navigation-bar-react
                const navBarLinks = document.querySelectorAll('.minutes-navigation-bar-react a');
                for (const link of navBarLinks) {
                    if (link.textContent.includes('PDF')) {
                        return link.href;
                    }
                }
                
                // If not found, try the icon-link-list
                const iconListLinks = document.querySelectorAll('.icon-link-list a');
                for (const link of iconListLinks) {
                    if (link.textContent.includes('PDF')) {
                        return link.href;
                    }
                }
                return null;
            }''')
            
            browser.close()
            
            if not pdf_link:
                raise ValueError(f"No PDF link found in transcript page: {url}")
                
            # Return tuple of (content, type) as required by new interface
            return pdf_link, 'pdf_link'
            
    except Exception as e:
        logger.error(f"Failed to extract PDF link from {url}: {str(e)}")
        raise ValueError(f"Failed to extract PDF link: {str(e)}") 