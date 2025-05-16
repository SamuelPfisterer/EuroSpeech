import re
import logging
from typing import Tuple, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Simplified selectors focused on MP4 content
DEFAULT_SELECTORS = [
    'video',
    'source',
    'a',
    '[src*=".mp4"]',
    '[href*=".mp4"]',
    'script[type="text/javascript"]'
]

def extract_video_url(url: str, selectors: List[str] = DEFAULT_SELECTORS) -> Optional[str]:
    """
    Extract MP4 video URL from the Norwegian parliament video page.
    
    Args:
        url: The URL of the page containing the video
        selectors: List of CSS selectors to search for video elements
    
    Returns:
        Optional[str]: The MP4 video URL if found, None otherwise
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        logger.info("Searching for MP4 video URL in page content...")
        
        # First, try to find MP4 URL in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            content = script.string
            if content:
                # Look for MP4 URL patterns
                mp4_matches = re.findall(r'https?://[^\s<>"\']+?\.mp4', content)
                if mp4_matches:
                    for match in mp4_matches:
                        try:
                            if requests.head(match, timeout=5).status_code == 200:
                                logger.info(f"Found valid MP4 URL in script: {match}")
                                return match
                        except:
                            continue
        
        # Check all potential video sources
        for selector in selectors:
            logger.debug(f"Checking selector: {selector}")
            elements = soup.select(selector)
            
            for element in elements:
                for attr in ['src', 'href', 'data-src', 'data-video', 'content']:
                    value = element.get(attr)
                    if value:
                        full_url = urljoin(url, value)
                        
                        if full_url.lower().endswith('.mp4'):
                            try:
                                if requests.head(full_url, timeout=5).status_code == 200:
                                    logger.info(f"Found valid MP4 URL: {full_url}")
                                    return full_url
                            except Exception as e:
                                logger.debug(f"Failed to verify URL {full_url}: {str(e)}")
                                continue
        
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

def process_video_link(url: str) -> Tuple[str, str]:
    """Extract downloadable MP4 video link from Norwegian parliament video page.
    
    Args:
        url: The video page URL to process
        
    Returns:
        tuple[str, str]: (downloadable_url, link_type) where
        link_type will be 'mp4_video_link'
        
    Raises:
        ValueError: If extraction fails
    """
    try:
        # Extract the video URL using the adapted function from get_video_stream.py
        video_url = extract_video_url(url)
        
        if not video_url:
            raise ValueError(f"No MP4 video URL found in page: {url}")
        
        # Since we're only looking for MP4s now, we can always return mp4_video_link
        return video_url, 'mp4_video_link'
            
    except Exception as e:
        logging.error(f"Failed to process video link {url}: {str(e)}")
        raise ValueError(f"Failed to extract video link: {str(e)}") 