import time
import random
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from tenacity import retry, stop_after_attempt, wait_exponential

def get_total_pages(soup: BeautifulSoup) -> int:
    """
    Helper Function: Extract the total number of pages from the pagination element.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        int: Total number of pages (defaults to 1 if no pagination found)
    """
    pagination = soup.find('ul', class_='pagination')
    if not pagination:
        return 1
        
    # Find all page items
    page_numbers = []
    for item in pagination.find_all('li', class_='page-item'):
        # Check both <a> and <span> elements for page numbers
        for element in [item.find('a', class_='page-link'), item.find('span', class_='page-link')]:
            if element and element.text.isdigit():
                page_numbers.append(int(element.text))
                
    return max(page_numbers) if page_numbers else 1

def extract_page_content(soup: BeautifulSoup) -> str:
    """
    Helper Function: Extract all transcript content from a single page.
    This function handles finding all transcript rows and extracting speaker names
    and transcript text from each row.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        str: Formatted string containing all speakers and their transcripts
    """
    result = ""
    transcript_rows = soup.find_all('div', class_='media-body js-eq-button-append speech-vertical-align-top')
    
    for row in transcript_rows:
        try:
            # Extract speaker name
            speaker = "Unknown Speaker"
            speaker_element = row.find('h4', class_='media-heading')
            if speaker_element and speaker_element.find('a'):
                speaker = speaker_element.find('a').text.strip()
            
            # Extract transcript text
            transcript_div = row.find('div', class_='transkript')
            if transcript_div:
                content_div = transcript_div.find('div', id=lambda x: x and x.endswith('-content'))
                if content_div:
                    # Convert <br> tags to newlines
                    for br in content_div.find_all('br'):
                        br.replace_with('\n')
                    
                    transcript_text = content_div.get_text(strip=True)
                    result += f"**{speaker}**\n{transcript_text}\n\n"
                    print(f"Extracted transcript for {speaker}")
                    
        except Exception as e:
            print(f"Error processing transcript row: {e}")
            
    return result

@browser(reuse_driver=False, headless=True)
#@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=5, max=60))
def processed_transcript_text_link(driver: Driver, url: str) -> str:
    """
    Process a transcript URL and return text content.
    This is the top lv function and uses multiple helper functions to actually perform the extraction.
    
    This function:
    1. Navigates to the provided URL
    2. Determines the total number of pages
    3. Processes each page to extract speakers and their transcripts
    4. Returns a formatted string containing all the content
    
    Args:
        driver: Botasaurus driver instance
        url: URL of the transcript page
        
    Returns:
        str: Formatted string containing all speakers and their transcripts
        
    Raises:
        ValueError: If transcript processing fails
    """
    try:
        result = ""
        
        # Initial page load
        print(f"Navigating to {url}")
        driver.get(url)
        time.sleep(10)
        
        # Get initial page content
        soup = soupify(driver)
        total_pages = get_total_pages(soup)
        print(f"Found {total_pages} pages to process")
        
        # Process first page
        result += extract_page_content(soup)
        
        # Process remaining pages
        for page in range(2, total_pages + 1):
            # Navigate to next page
            page_url = f"{url}?page={page}"
            print(f"Navigating to page {page}: {page_url}")
            driver.get(page_url)
            time.sleep(10)
            
            # Process page content
            soup = soupify(driver)
            result += extract_page_content(soup)
            
            # Random delay between pages
            if page < total_pages:
                time.sleep(random.uniform(2, 5))
                
        return result
        
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

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
        return processed_transcript_text_link(url)
    except Exception as e:
        raise ValueError(f"Failed to process text transcript: {str(e)}")

# def main():
    # url_long = "https://otvoreniparlament.rs/transkript/8068"
    # url_short = "https://otvoreniparlament.rs/transkript/8072"

    # try:
    #     print(f"Processing transcript from URL: {url_long}")
    #     transcript_text = processed_transcript_text_link(url_long)
        
    #     output_file = "transcript_output.txt"
    #     with open(output_file, "w", encoding="utf-8") as f:
    #         f.write(transcript_text)
        
    #     print(f"Successfully processed transcript from {url_long}")
    #     print(f"Output saved to {output_file}")
        
    # except Exception as e:
    #     print(f"Error processing transcript: {e}")

    # if __name__ == "__main__":
    #     main()
