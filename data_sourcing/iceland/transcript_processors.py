import re
from camoufox.sync_api import Camoufox
from playwright.sync_api import Page, Error as PlaywrightError
from typing import Optional
import os

# Re-use proxy settings for testing consistency
PROXY = {
    'server': 'gate.decodo.com:7000',
    'username': 'sph4b47do7',
    'password': 'fsv5fKD+wvTzLwt628'
}

# Regex pattern to identify the intermediate link - more general version
INTERMEDIATE_LINK_PATTERN = re.compile(r"https?://(?:www\.)?althingi\.is/altext/\d+/\d+/")
# Prefix for the final speech link
SPEECH_LINK_PREFIX = "http://www.althingi.is/altext/raeda/"

def find_first_speech_link(page: Page, transcript_url: str) -> Optional[str]:
    """
    Navigates through intermediate links to find the first speech link.

    Args:
        page: The Playwright/Camoufox page object.
        transcript_url: The initial transcript URL (e.g., .../fXXX.sgml).

    Returns:
        The URL of the first speech link found, or None if any step fails.
    """
    try:
        print(f"Processing transcript: {transcript_url}")
        page.goto(transcript_url, wait_until='domcontentloaded', timeout=60000)

        # Get all potential intermediate links
        potential_links = page.query_selector_all('a[href*="/altext/"]')
        intermediate_links = []
        
        # Filter links matching our pattern
        for link in potential_links:
            href = link.get_attribute('href')
            if href and INTERMEDIATE_LINK_PATTERN.search(href):
                intermediate_links.append(href)
        
        if not intermediate_links:
            print(f"Could not find any intermediate links on {transcript_url}")
            return None
        
        # Try up to 10 intermediate links
        for i, intermediate_url in enumerate(intermediate_links[:10]):
            print(f"Trying intermediate link {i+1}/{min(10, len(intermediate_links))}: {intermediate_url}")
            
            try:
                # Navigate to the intermediate link
                page.goto(intermediate_url, wait_until='domcontentloaded', timeout=60000)
                
                # Look for speech link on this page
                speech_link_element = page.query_selector(f'a[href^="{SPEECH_LINK_PREFIX}"]')
                
                if speech_link_element:
                    speech_url = speech_link_element.get_attribute('href')
                    print(f"Found speech link: {speech_url}")
                    return speech_url
                else:
                    print(f"No speech link found on {intermediate_url}, trying next link...")
            except Exception as e:
                print(f"Error navigating to {intermediate_url}: {e}")
                continue  # Try the next link
        
        print("Exhausted all candidate intermediate links without finding a speech link")
        return None

    except PlaywrightError as e:
        print(f"Playwright error during processing: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def extract_speech_content(page: Page, speech_url: str) -> tuple[str, Optional[str]]:
    """
    Extracts speech content and metadata from a speech page.
    
    Args:
        page: The Playwright/Camoufox page object.
        speech_url: URL of the speech page.
        
    Returns:
        Tuple containing:
        - String with formatted speech content and metadata
        - URL of the next speech, or None if there isn't one
    """
    try:
        page.goto(speech_url, wait_until='domcontentloaded', timeout=60000)
        
        # Create a buffer for the content
        content = []
        
        # Extract metadata
        metadata_div = page.query_selector('.raedu_titill')
        if metadata_div:
            # Get timestamp
            time_div = metadata_div.query_selector('.main-timi')
            timestamp = time_div.text_content().strip() if time_div else "No timestamp"
            
            # Get video link
            video_link = "No video link"
            video_element = metadata_div.query_selector('a[href*="/altext/upptokur/raeda/"]')
            if video_element:
                video_link = video_element.get_attribute('href')
            
            # Get speaker info
            speaker_element = metadata_div.query_selector('h2.fyrsti_stafur')
            speaker_info = speaker_element.text_content().strip() if speaker_element else "No speaker info"
            
            # Format metadata
            content.append(f"METADATA_BEGIN")
            content.append(f"SPEECH_URL: {speech_url}")
            content.append(f"TIMESTAMP: {timestamp}")
            content.append(f"VIDEO_LINK: {video_link}")
            content.append(f"SPEAKER: {speaker_info}")
            content.append(f"METADATA_END")
        else:
            content.append(f"METADATA_BEGIN")
            content.append(f"SPEECH_URL: {speech_url}")
            content.append(f"ERROR: No metadata found")
            content.append(f"METADATA_END")
        
        # Extract speech text
        content.append(f"SPEECH_BEGIN")
        speech_div = page.query_selector('#raeda_efni')
        if speech_div:
            # Get all paragraphs
            paragraphs = speech_div.query_selector_all('p.ind')
            for p in paragraphs:
                content.append(p.text_content().strip())
        else:
            content.append("ERROR: No speech content found")
        content.append(f"SPEECH_END")
        
        # Check for next speech link
        next_speech_url = None
        next_div = page.query_selector('div.right a:has-text("Næsta ræða")')
        if next_div:
            next_speech_url = next_div.get_attribute('href')
            print(f"Found next speech link: {next_speech_url}")
        
        return "\n".join(content), next_speech_url
        
    except Exception as e:
        print(f"Error extracting speech content: {e}")
        return f"ERROR: Failed to extract content from {speech_url}\nError: {str(e)}", None

def process_full_transcript(page: Page, first_speech_url: str) -> str:
    """
    Processes a full transcript by following all "next speech" links.
    
    Args:
        page: The Playwright/Camoufox page object.
        first_speech_url: URL of the first speech.
        
    Returns:
        String containing all speech content and metadata.
    """
    all_content = []
    current_url = first_speech_url
    speech_count = 0
    
    while current_url:
        speech_count += 1
        print(f"Processing speech #{speech_count}: {current_url}")
        
        content, next_url = extract_speech_content(page, current_url)
        all_content.append(content)
        
        # Add separator between speeches
        if next_url:
            all_content.append("\n--- NEXT_SPEECH ---\n")
        
        current_url = next_url
    
    print(f"Processed {speech_count} speeches in total")
    return "\n".join(all_content)

def extract_full_transcript(page: Page, transcript_url: str) -> Optional[str]:
    """
    Extracts full transcript content from a transcript URL.
    
    Args:
        page: The Playwright/Camoufox page object.
        transcript_url: Initial transcript URL.
        
    Returns:
        String containing all content, or None if failed.
    """
    # Find the first speech link
    first_speech_url = find_first_speech_link(page, transcript_url)
    if not first_speech_url:
        return None
    
    # Process the full transcript by following all "next speech" links
    return process_full_transcript(page, first_speech_url)

def main():
    """Main function to test the transcript extraction."""
    test_url = "https://www.althingi.is/altext/144/f066.sgml"  # Example URL provided
    output_file = "transcript_output.txt"
    
    print(f"Starting extraction from {test_url}")
    try:
        with Camoufox(
            geoip=True,
            proxy=PROXY,
            headless=False
        ) as browser:
            page = browser.new_page()
            full_content = extract_full_transcript(page, test_url)
            
            if full_content:
                # Write to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                print(f"\nTranscript successfully extracted and saved to {output_file}")
                print(f"File size: {os.path.getsize(output_file) / 1024:.2f} KB")
            else:
                print(f"\nFailed to extract transcript from {test_url}")
    
    except Exception as e:
        print(f"Failed to initialize or run Camoufox: {e}")

if __name__ == "__main__":
    main()
