"""Video link extractor for the Danish Parliament."""

from typing import Tuple
import logging
import traceback
import time
import requests
from playwright.sync_api import sync_playwright

def extract_src_url(page):
    """Extract src_url from the video element.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: The extracted source URL
        
    Raises:
        ValueError: If extraction fails
    """
    try:
        logging.info("Searching for video player...")
        
        # Find the outer iframe (mobiltv)
        logging.info("Looking for mobiltv iframe...")
        outer_iframe = page.wait_for_selector('iframe[src*="mobiltv.ft.dk"]', timeout=10000)
        if not outer_iframe:
            raise ValueError("No mobiltv iframe found")
            
        # Get outer iframe content
        logging.info("Getting content frame for mobiltv iframe...")
        outer_frame = outer_iframe.content_frame()
        if not outer_frame:
            raise ValueError("Could not get content frame for mobiltv iframe")
        
        # Wait for frame to load
        logging.info("Waiting for outer frame to load...")
        time.sleep(3)
        
        # Find Kaltura iframe within the outer frame
        logging.info("Looking for Kaltura iframe...")
        inner_iframe = outer_frame.wait_for_selector('iframe[id*="kaltura_player"]', timeout=10000)
        if not inner_iframe:
            raise ValueError("No Kaltura iframe found")
        
        # Get Kaltura iframe content
        logging.info("Getting content frame for Kaltura iframe...")
        kaltura_frame = inner_iframe.content_frame()
        if not kaltura_frame:
            raise ValueError("Could not get content frame for Kaltura iframe")
        
        # Wait for frame to load
        logging.info("Waiting for Kaltura frame to load...")
        time.sleep(3)
        
        # Find video element
        logging.info("Looking for video element...")
        video = kaltura_frame.wait_for_selector('video', timeout=10000)
        if not video:
            raise ValueError("No video element found")
        
        # Extract src attribute
        logging.info("Extracting src attribute...")
        src_url = video.get_attribute('src')
        if not src_url:
            raise ValueError("No src attribute found on video element")
            
        logging.info(f"Found src_url: {src_url}")
        return src_url
    
    except Exception as e:
        logging.error(f"Error extracting video src: {str(e)}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
        raise ValueError(f"Error extracting video src: {str(e)}")

def follow_redirect(src_url: str) -> str:
    """Follow redirects to get the final MP3 URL.
    
    Args:
        src_url: The source URL to follow
        
    Returns:
        str: The final MP3 URL
        
    Raises:
        ValueError: If redirect following fails
    """
    if not src_url:
        raise ValueError("No source URL provided")
        
    logging.info(f"Following redirects for: {src_url}")
    
    try:
        # Set headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.ft.dk/'
        }
        
        # Follow redirects using requests (synchronous)
        logging.info(f"Making request to: {src_url}")
        response = requests.get(src_url, headers=headers, allow_redirects=True)
        logging.info(f"Response status: {response.status_code}")
        final_url = str(response.url)
        logging.info(f"Final URL after redirects: {final_url}")
        return final_url
    
    except Exception as e:
        logging.error(f"Error following redirects: {str(e)}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
        raise ValueError(f"Error following redirects: {str(e)}")

def process_video_link(url: str) -> Tuple[str, str]:
    """Extract downloadable video link from the Danish Parliament video page.
    
    Args:
        url: The video page URL to process
        
    Returns:
        tuple[str, str]: (downloadable_url, link_type)
        
    Raises:
        ValueError: If extraction fails
    """
    logging.info(f"process_video_link called with URL: {url}")
    browser = None
    try:
        logging.info(f"Starting video extraction process for URL: {url}")
        with sync_playwright() as playwright:
            logging.info("Launching browser...")
            # Launch browser
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Navigate to the URL
            logging.info(f"Navigating to URL: {url}")
            page.goto(url, timeout=60000)
            
            # Wait for page to load
            logging.info("Waiting for page to load...")
            time.sleep(5)
            
            # Extract src_url
            logging.info("Extracting source URL...")
            src_url = extract_src_url(page)
            
            # Close browser
            logging.info("Closing browser...")
            browser.close()
            browser = None
            
            # Follow redirects to get MP3 URL
            if src_url:
                logging.info("Following redirects...")
                mp3_url = follow_redirect(src_url)
                logging.info(f"Successfully extracted MP3 URL: {mp3_url}")
                return mp3_url, 'generic_video_link'
            else:
                raise ValueError("Failed to extract source URL")
    
    except Exception as e:
        logging.error(f"Failed to process video link {url}: {str(e)}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
        if browser:
            logging.info("Closing browser after error...")
            browser.close()
        raise ValueError(f"Failed to extract video link: {str(e)}") 