import cloudscraper
from bs4 import BeautifulSoup
import logging
import time
import random
from typing import Union

def process_transcript_html(url: str) -> str:
    """
    Process a transcript URL and return HTML content from the Icelandic Parliament website.
    
    Args:
        url: The URL to process
        
    Returns:
        str: The processed HTML content
        
    Raises:
        ValueError: If processing fails
        Any other exceptions that occur during processing
    """
    try:
        # Add delay to avoid overwhelming the server
        time.sleep(random.uniform(3, 7))  # 3-7 seconds between requests
        
        # Initialize cloudscraper to bypass any scraping protections
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # Get the main transcript page
        response = scraper.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve page: Status code {response.status_code}")
            
        # Find the transcript content div
        soup = BeautifulSoup(response.text, 'html.parser')
        transcript_div = soup.find('div', id='raeda_efni')
        
        if not transcript_div:
            raise ValueError("No transcript content found (div#raeda_efni not found)")
        
        # Return the HTML content of the transcript div
        return str(transcript_div)
        
    except Exception as e:
        raise ValueError(f"Failed to process HTML transcript: {str(e)}")

def process_transcript_text(url: str) -> str:
    """
    Process a transcript URL and return plain text content from the Icelandic Parliament website.
    
    Args:
        url: The URL to process
        
    Returns:
        str: The processed text content
        
    Raises:
        ValueError: If processing fails
        Any other exceptions that occur during processing
    """
    try:
        # Add delay to avoid overwhelming the server
        time.sleep(random.uniform(3, 7))  # 3-7 seconds between requests
        
        # Initialize cloudscraper to bypass any scraping protections
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # Get the main transcript page
        response = scraper.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve page: Status code {response.status_code}")
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the transcript content div
        transcript_div = soup.find('div', id='raeda_efni')
        if not transcript_div:
            raise ValueError("No transcript content found (div#raeda_efni not found)")
        
        # Get all paragraphs and join their text
        paragraphs = transcript_div.find_all('p')
        transcript_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        if not transcript_text:
            raise ValueError("No text content found in transcript div")
            
        return transcript_text
        
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}") 