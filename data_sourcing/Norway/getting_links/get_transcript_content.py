from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Optional
import logging
from pathlib import Path
from getting_speech_segments import extract_speeches_with_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_content_sections(soup: BeautifulSoup) -> List[Dict]:
    """Extract content sections from legacy format page."""
    sections = []
    content_list = soup.select_one('ul.document-content-list-react__list')
    
    if content_list:
        for item in content_list.find_all('li', class_='document-content-list-react__list-item'):
            link_elem = item.select_one('a.document-content-list-react__list-item__heading-link')
            if link_elem:
                section_title = link_elem.get_text(strip=True)
                section_url = 'https://www.stortinget.no' + link_elem['href']
                sections.append({
                    'title': section_title,
                    'url': section_url
                })
    
    return sections

def extract_legacy_speeches(soup: BeautifulSoup, section_title: str) -> List[Dict]:
    """Extract speeches from legacy format HTML."""
    speeches = []
    
    # Find the content area
    content_area = soup.find('div', class_='content-area-react')
    if not content_area:
        return []
    
    # Find the rich text container
    rich_text = content_area.find('div', class_='rich-text-theme-big-doc')
    if not rich_text:
        return []
    
    # Find all paragraphs that contain speeches
    paragraphs = rich_text.find_all('p', class_='ref-uinnrykk')
    
    current_speech = None
    
    for p in paragraphs:
        # Check if this is a new speech
        speaker_link = p.find('a', class_='ref-innlegg-navn')
        president_span = p.find('span', class_='ref-presidenten')
        
        if speaker_link or president_span:
            # Save previous speech if exists
            if current_speech and current_speech['text']:
                speeches.append(current_speech)
            
            # Start new speech
            current_speech = {
                "speech_id": "legacy",
                "speech_type": "legacy_speech",
                "speaker": "",
                "text": "",
                "time_stamp": "No Time-Stamp",
                "video_link": None,
                "video_time_stamp": "No Video Time-Stamp",
                "section_title": section_title
            }
            
            # Extract speaker and timestamp
            if speaker_link:
                current_speech['speaker'] = speaker_link.get_text(strip=True)
                # Look for video link
                video_link = p.find('a', class_='ref-innlegg-video')
                if video_link:
                    current_speech['video_link'] = 'https://www.stortinget.no' + video_link['href']
                    time_span = video_link.find('span')
                    if time_span:
                        current_speech['time_stamp'] = time_span.get_text(strip=True).strip('[]')
                    if 'msid=' in video_link['href']:
                        current_speech['video_time_stamp'] = video_link['href'].split('msid=')[-1].split('&')[0]
            elif president_span:
                current_speech['speaker'] = president_span.get_text(strip=True)
            
            # Get the text content
            text = p.get_text(strip=True)
            if text.startswith(current_speech['speaker']):
                text = text[len(current_speech['speaker']):].strip(':').strip()
            current_speech['text'] = text
        
        elif current_speech:
            # Append text to current speech
            current_speech['text'] += ' ' + p.get_text(strip=True)
    
    # Don't forget to add the last speech
    if current_speech and current_speech['text']:
        speeches.append(current_speech)
    
    return speeches

def process_transcript(url: str) -> Optional[List[Dict]]:
    """Process a transcript URL, handling both modern and legacy formats."""
    try:
        # Try modern format first (?all=true)
        all_content_url = f"{url.rstrip('/')}/?all=true"
        logging.info(f"Trying modern format: {all_content_url}")
        
        speeches = extract_speeches_with_playwright(all_content_url)
        if speeches:
            logging.info("Successfully extracted speeches using modern format")
            return speeches
        
        # Fallback to legacy format
        logging.info(f"Falling back to legacy format for: {url}")
        
        # Use a single Playwright instance for the entire legacy process
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            try:
                logging.info(f"Getting sections from: {url}")
                page.goto(url)
                
                # Wait for content list
                try:
                    page.wait_for_selector('.document-content-list-react__list', timeout=30000)
                except Exception as e:
                    logging.warning(f"Content list not found: {str(e)}")
                    return None
                
                # Wait extra time for any additional scripts
                time.sleep(5)
                
                # Get the sections
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                sections = get_content_sections(soup)
                
                if not sections:
                    logging.warning("No content sections found in legacy format")
                    return None
                
                # Process each section using the same page
                all_speeches = []
                for section in sections:
                    logging.info(f"Processing section: {section['title']}")
                    try:
                        # Navigate to section
                        page.goto(section['url'])
                        
                        # Wait for content to load
                        try:
                            page.wait_for_selector('.content-area-react', timeout=30000)
                        except Exception:
                            logging.warning(f"Content area not found in section {section['title']}")
                            continue
                        
                        time.sleep(5)  # Extra wait to ensure content is loaded
                        
                        # Get and process content
                        section_html = page.content()
                        section_soup = BeautifulSoup(section_html, 'html.parser')
                        
                        # Extract speeches using legacy format
                        section_speeches = extract_legacy_speeches(section_soup, section['title'])
                        if section_speeches:
                            logging.info(f"Found {len(section_speeches)} speeches in section {section['title']}")
                            all_speeches.extend(section_speeches)
                        
                    except Exception as e:
                        logging.error(f"Error processing section {section['title']}: {str(e)}")
                    time.sleep(1)  # Be nice to the server
                
                return all_speeches if all_speeches else None
                
            finally:
                browser.close()
                
    except Exception as e:
        logging.error(f"Error processing transcript {url}: {str(e)}")
        return None

def main():
    # Load transcript links
    df = pd.read_csv('transcript_links_with_dates.csv')
    
    # Create output directory
    output_dir = Path('new_transcript_retrieval')
    output_dir.mkdir(exist_ok=True)
    
    # Test with a specific 2013 URL
    test_url = "https://www.stortinget.no/no/Saker-og-publikasjoner/Publikasjoner/Referater/Stortinget/2012-2013/130109/"
    
    logging.info(f"\nTesting URL from 2013: {test_url}")
    speeches = process_transcript(test_url)
    
    if speeches:
        logging.info(f"Successfully extracted {len(speeches)} speeches")
        # Save to CSV for inspection
        output_file = output_dir / f"test_speeches_{test_url.split('/')[-2]}.csv"
        df = pd.DataFrame(speeches)
        df.to_csv(output_file, index=False)
        logging.info(f"Saved speeches to {output_file}")
    else:
        logging.error(f"Failed to extract speeches from {test_url}")
    
    logging.info("-" * 80)

if __name__ == "__main__":
    main() 