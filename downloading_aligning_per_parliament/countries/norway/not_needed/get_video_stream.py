import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
import pandas as pd
import os
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SELECTORS = [
    'video',
    'source',
    'a',
    'link',
    '[type*="video"]',
    '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',
    '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]',
    'script[type="text/javascript"]'  # Added to check for video URLs in scripts
]

DEFAULT_MEDIA_EXTENSIONS = [
    '.mp4', '.m4v', '.m4s', '.m3u8', '.m3u', '.mpd',
    '.webm', '.mkv', '.ts', '.mov', '.avi'
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_video_url(url: str, selectors: List[str] = DEFAULT_SELECTORS, 
                 media_extensions: List[str] = DEFAULT_MEDIA_EXTENSIONS) -> Optional[str]:
    """
    Extract video URL using BeautifulSoup.
    
    Args:
        url: The URL of the page containing the video
        selectors: List of CSS selectors to search for video elements
        media_extensions: List of valid video file extensions
    
    Returns:
        Optional[str]: The video URL if found, None otherwise
    """
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        logger.info("Searching for video URL in page content...")
        
        # First, try to find video URL in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            content = script.string
            if content:
                # Look for common video URL patterns
                mp4_matches = re.findall(r'https?://[^\s<>"\']+?\.mp4', content)
                if mp4_matches:
                    for match in mp4_matches:
                        try:
                            if requests.head(match, timeout=5).status_code == 200:
                                logger.info(f"Found valid video URL in script: {match}")
                                return match
                        except:
                            continue
        
        # Check all potential video sources
        for selector in selectors:
            logger.debug(f"Checking selector: {selector}")
            elements = soup.select(selector)
            logger.debug(f"Found {len(elements)} elements for selector {selector}")
            
            for element in elements:
                # Log the element for debugging
                logger.debug(f"Checking element: {element}")
                
                for attr in ['src', 'href', 'data-src', 'data-video', 'content']:
                    if value := element.get(attr):
                        logger.debug(f"Found attribute {attr} with value: {value}")
                        full_url = urljoin(url, value)
                        
                        if any(full_url.lower().endswith(ext) for ext in media_extensions):
                            try:
                                if requests.head(full_url, timeout=5).status_code == 200:
                                    logger.info(f"Found valid video URL: {full_url}")
                                    return full_url
                            except Exception as e:
                                logger.debug(f"Failed to verify URL {full_url}: {str(e)}")
                                continue
        
        # If no direct video URL found, save the HTML for inspection
        debug_file = "debug_page.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info(f"Saved page HTML to {debug_file} for inspection")
        
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

def main():
    """Test function with random video links from combined_links.csv"""
    # Get the path to combined_links.csv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '..', 'output', 'combined_links.csv')
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Select 4 random video links
    sample_rows = df.sample(n=4, random_state=42)
    
    print("\nTesting with 4 random video links from combined_links.csv:\n")
    
    for idx, row in sample_rows.iterrows():
        print(f"\nTesting video from {row['date']}:")
        print(f"Video URL: {row['video_url']}")
        
        video_url = get_video_url(row['video_url'])
        print(f"Found video URL: {video_url}")
        print("-" * 80)

if __name__ == "__main__":
    # Set debug logging for development
    logging.getLogger().setLevel(logging.DEBUG)
    main() 