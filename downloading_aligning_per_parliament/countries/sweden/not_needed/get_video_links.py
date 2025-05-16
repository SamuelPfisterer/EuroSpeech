import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_video_url(url: str, selectors: List[str], media_extensions: List[str]) -> Optional[str]:
    """
    Extract video URL from a webpage using specified selectors and media extensions.
    
    Args:
        url: The webpage URL to search for video links
        selectors: List of CSS selectors to find video elements
        media_extensions: List of valid video file extensions
    
    Returns:
        Optional[str]: The found video URL or None if not found
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check all potential video sources
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                for attr in ['src', 'href', 'data-src', 'data-video']:
                    if value := element.get(attr):
                        video_url = urljoin(url, value)
                        if any(video_url.lower().endswith(ext) for ext in media_extensions):
                            try:
                                if requests.head(video_url, timeout=5).status_code == 200:
                                    logging.info(f"Found valid video URL: {video_url}")
                                    return video_url
                            except Exception as e:
                                logging.warning(f"Failed to verify URL {video_url}: {str(e)}")
                                continue
        
        logging.info("No valid video URLs found")
        return None
    
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
        return None

def main():
    # Default parameters as specified
    default_selectors = [
        'video', 'source', 'a', 'link', 
        '[type*="video"]',
        '[src*=".mp4"], [src*=".m3u8"], [src*=".mpd"]',
        '[href*=".mp4"], [href*=".m3u8"], [href*=".mpd"]'
    ]
    
    default_media_extensions = [
        '.mp4', '.m4v', '.m4s', '.m3u8', '.m3u', 
        '.mpd', '.webm', '.mkv', '.ts', '.mov', '.avi'
    ]
    
    # Example usage with the same URL as the transcript
    test_url = "https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/utgiftsomrade-8-migration_hc01sfu4/"
    result = get_video_url(test_url, default_selectors, default_media_extensions)
    
    if result:
        print(f"Found video URL: {result}")
    else:
        print("No video URL found")

if __name__ == "__main__":
    main() 