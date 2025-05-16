import requests
from bs4 import BeautifulSoup
from typing import Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_video_link(url: str) -> Tuple[str, str]:
    """Extract downloadable link from video page.
    
    Args:
        url: The video page URL to process
        
    Returns:
        tuple[str, str]: (downloadable_url, link_type) where
        link_type is one of: 'mp4_video_link', 'm3u8_link', etc.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # List of selectors to try
        selectors = [
            'video', 'source', 'a', 'link', 
            '[type*="video"]',
            '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',
            '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]'
        ]
        
        # Media extensions and their corresponding link types
        media_types = {
            '.mp4': 'mp4_video_link',
            '.m3u8': 'm3u8_link',
            '.mpd': 'generic_video_link',
            '.ts': 'generic_video_link',
            '.m4v': 'mp4_video_link',
            '.m4s': 'generic_video_link',
            '.webm': 'generic_video_link',
            '.mkv': 'generic_video_link',
            '.mov': 'mp4_video_link',
            '.avi': 'generic_video_link'
        }
        
        # Check all potential video sources
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                for attr in ['src', 'href', 'data-src', 'data-video']:
                    if value := element.get(attr):
                        video_url = requests.compat.urljoin(url, value)
                        
                        # Determine link type based on extension
                        for ext, link_type in media_types.items():
                            if video_url.lower().endswith(ext):
                                try:
                                    # Verify URL is accessible
                                    if requests.head(video_url, timeout=5).status_code == 200:
                                        logging.info(f"Found valid video URL: {video_url} of type {link_type}")
                                        return video_url, link_type
                                except Exception as e:
                                    logging.warning(f"Failed to verify URL {video_url}: {str(e)}")
                                    continue
        
        # If no direct media URL found, look for m3u8 in page source
        m3u8_urls = find_m3u8_in_source(response.text)
        if m3u8_urls:
            logging.info(f"Found m3u8 URL in source: {m3u8_urls[0]}")
            return m3u8_urls[0], 'm3u8_link'
        
        logging.error(f"No valid video URL found for {url}")
        raise ValueError(f"Failed to extract video link from {url}")
        
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
        raise ValueError(f"Failed to extract video link: {str(e)}")

def find_m3u8_in_source(html_content: str) -> list:
    """Find m3u8 URLs in page source."""
    import re
    pattern = r'https?://[^\s<>"]+?\.m3u8'
    return re.findall(pattern, html_content) 