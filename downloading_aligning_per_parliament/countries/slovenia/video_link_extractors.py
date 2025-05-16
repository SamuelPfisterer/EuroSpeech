from camoufox.sync_api import Camoufox
import json
from typing import Tuple

def process_video_link(url: str) -> Tuple[str, str]:
    """
    Extracts a downloadable video link (m3u8 format) from a given video page URL.
    
    This function uses the Camoufox browser automation to:
    1. Monitor network requests for m3u8 URLs
    2. Fall back to extracting m3u8 URL from JSON-LD script tag if not found in network requests
    3. Return the extracted m3u8 URL and its type
    
    Args:
        url (str): The URL of the video page to process. This should be a direct link
                  to a video player page that contains either m3u8 network requests
                  or JSON-LD metadata with the video content URL.
    
    Returns:
        tuple[str, str]: A tuple containing:
            - The extracted m3u8 URL (str)
            - The link type identifier 'm3u8_link' (str)
    
    Raises:
        ValueError: If no m3u8 URL could be extracted from the page
    
    Example:
        >>> url = "https://365.rtvslo.si/embed/175114129?a=1&d=1"
        >>> m3u8_url, link_type = process_video_link(url)
        >>> print(m3u8_url)
        'https://example.com/video/playlist.m3u8'
    """
    try:
        with Camoufox(headless=True) as browser:  # Set headless=True
            page = browser.new_page()
            m3u8_url = None

            # Monitor network requests for m3u8 URLs
            def handle_request(request):
                nonlocal m3u8_url
                if "m3u8" in request.url:
                    m3u8_url = request.url

            page.on("request", handle_request)
            page.goto(url)
            
            # Fallback: Extract m3u8 URL from JSON-LD metadata if not found in network requests
            if not m3u8_url:
                script_selector = 'script#__jw-ld-json'
                if page.locator(script_selector).count() > 0:
                    script_content = page.locator(script_selector).text_content()
                    json_data = json.loads(script_content)
                    m3u8_url = json_data.get("contentUrl")
            
            if not m3u8_url:
                raise ValueError("Could not find m3u8 URL")
                
            return m3u8_url, 'm3u8_link'
    except Exception as e:
        raise ValueError(f"Failed to extract video link: {str(e)}")

# if __name__ == "__main__":
#     # Example usage
#     url = "https://365.rtvslo.si/embed/175114129?a=1&d=1"
#     m3u8_url, link_type = process_video_link(url)
#     print(m3u8_url)
