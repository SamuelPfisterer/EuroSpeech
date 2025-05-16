"""Video link extractor for Italian Parliament (Senato) videos.

This module extracts m3u8 playlist URLs from Italian Senate video pages.
It uses Playwright to monitor network requests and capture the streaming URL.
"""

import logging
import asyncio
from typing import Optional, Tuple
import time
from playwright.sync_api import sync_playwright

def extract_senato_m3u8(url: str, max_wait_time: int = 8) -> str:
    """Extract m3u8 playlist URL from Italian Senate video page.
    
    Args:
        url: The video page URL to process
        max_wait_time: Maximum time to wait for the m3u8 URL to appear
        
    Returns:
        str: The extracted m3u8 playlist URL
        
    Raises:
        ValueError: If no m3u8 URL is found within max_wait_time
    """
    try:
        final_url = None
        start_time = time.time()
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Function to handle network requests
            def handle_request(request):
                nonlocal final_url
                if final_url:  # Skip if we already found our URL
                    return
                    
                request_url = request.url
                # Look specifically for the main playlist m3u8
                if 'playlist.m3u8' in request_url.lower() and 'senato-vod' in request_url.lower():
                    final_url = request_url
                    elapsed = time.time() - start_time
                    logging.info(f"[{elapsed:.2f}s] Found streaming URL: {request_url}")
            
            # Monitor all requests
            page.on('request', handle_request)
            
            # Navigate to the page
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Wait for the streaming URL or timeout
            wait_start = time.time()
            while not final_url and (time.time() - wait_start) < max_wait_time:
                time.sleep(0.1)  # Quick check every 100ms
            
            # Cleanup
            context.close()
            browser.close()
            
            if not final_url:
                raise ValueError(f"No streaming URL found for {url} after {max_wait_time} seconds")
            
            return final_url
            
    except Exception as e:
        raise ValueError(f"Failed to extract m3u8 URL from {url}: {str(e)}")

def process_video_link(url: str) -> Tuple[str, str]:
    """
    Process a video page URL and return the actual downloadable link and its type.
    
    Args:
        url: The URL to process
        
    Returns:
        Tuple[str, str]: (downloadable_url, link_type)
        where link_type is one of: 'mp4_video_link', 'm3u8_link', etc.
        matching the keys in DOWNLOAD_FUNCTIONS
        
    Raises:
        Any exception that occurs during processing
    """
    try:
        if 'webtv.senato.it' not in url:
            raise ValueError(f"URL {url} is not a valid Italian Senate video URL")
            
        # Extract the m3u8 URL
        m3u8_url = extract_senato_m3u8(url)
        
        return m3u8_url, 'm3u8_link'
        
    except Exception as e:
        logging.error(f"Failed to process video link {url}: {str(e)}")
        raise ValueError(f"Failed to extract video link: {str(e)}") 