import time
import random
import logging
from typing import Union
from bs4 import BeautifulSoup
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.browser import Wait

def process_transcript_html(url: str) -> str:
    """
    Process a transcript URL and return HTML content.
    
    Args:
        url: The URL to process
        
    Returns:
        str: The processed HTML content
        
    Raises:
        ValueError: If processing fails
        Any other exceptions that occur during processing
    """
    try:
        # Use Botasaurus processor to fetch content
        result = transcript_html_processor(url)
        
        logging.info(f"Result from transcript_html_processor: {type(result)}")
        logging.info(f"Keys in result: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        # If not successful, raise error with the message
        if not result["success"]:
            raise ValueError(result["error"])
            
        # Add debugging for the content type
        html_content = result["html_content"]
        logging.info(f"Type of html_content: {type(html_content)}")
        
        # Make sure html_content is a string, not a dict
        if isinstance(html_content, dict):
            logging.warning(f"html_content is a dict, not a string: {html_content}")
            # Try to get the actual content from the dict if possible
            if "content" in html_content:
                html_content = html_content["content"]
            else:
                # Convert the dict to a string representation if we can't get the content
                html_content = str(html_content)
                
        # Return the HTML content
        return html_content
        
    except Exception as e:
        logging.error(f"Error in process_transcript_html: {str(e)}")
        raise ValueError(f"Failed to process HTML transcript: {str(e)}")

def process_transcript_text(url: str) -> str:
    """
    Process a transcript URL and return plain text content.
    
    Args:
        url: The URL to process
        
    Returns:
        str: The processed text content
        
    Raises:
        ValueError: If processing fails
        Any other exceptions that occur during processing
    """
    try:
        # Use Botasaurus processor to fetch content
        result = transcript_text_processor(url)
        
        # If not successful, raise error with the message
        if not result["success"]:
            raise ValueError(result["error"])
            
        # Return the text content
        return result["text_content"]
        
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

@browser(
    reuse_driver=True,
    headless=True,
    proxy= "http://island:ausgeTrickst=)@168.151.206.16:20000"
)
def transcript_html_processor(driver: Driver, url: str):
    """
    Botasaurus processor function to fetch HTML content.
    
    Args:
        driver: Botasaurus driver
        url: URL to process
        
    Returns:
        dict: Result object with success flag and content
    """
    try:
        # Add random delay to avoid detection patterns
        time.sleep(random.uniform(3, 7))
        
        logging.info(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(2)  # Add small delay
        
        # Get the page HTML directly
        page_html = driver.page_html
        
        # Add debugging to check the type of page_html
        logging.info(f"Type of page_html: {type(page_html)}")
        
        # Return the HTML content of the transcript div
        return {
            "success": True,
            "html_content": page_html
        }
        
    except Exception as e:
        logging.error(f"Error in transcript_html_processor: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@browser(
    reuse_driver=True,
    headless=True,
    proxy= "http://island:ausgeTrickst=)@168.151.206.16:20000"
)
def transcript_text_processor(driver: Driver, url: str):
    """
    Botasaurus processor function to fetch text content.
    
    Args:
        driver: Botasaurus driver
        url: URL to process
        
    Returns:
        dict: Result object with success flag and content
    """
    try:
        # Add random delay to avoid detection patterns
        time.sleep(random.uniform(3, 7))
        
        logging.info(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(2)  # Add small delay
                
        
        # Get the page source as BeautifulSoup object
        soup = soupify(driver)
        
        # Find the transcript content div
        transcript_div = soup.find('div', id='raeda_efni')
        if not transcript_div:
            return {
                "success": False,
                "error": "No transcript content found (div#raeda_efni not found)"
            }
        
        # Get all paragraphs and join their text
        paragraphs = transcript_div.find_all('p')
        transcript_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        if not transcript_text:
            return {
                "success": False,
                "error": "No text content found in transcript div"
            }
            
        return {
            "success": True,
            "text_content": transcript_text
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }