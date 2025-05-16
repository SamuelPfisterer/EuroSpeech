import csv
import time
import re
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright
from urllib.parse import urljoin


NUM_PAGES = 179


def format_date(date_string):
    """
    Formats a date string into ddmmyyyy format.

    Args:
        date_string (str): The date string to format (e.g., "1992-03-11").

    Returns:
        str: The formatted date string (e.g., "11031992").
    """
    try:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_string)
        if match:
            year, month, day = match.groups()
            return f"{day}{month}{year}"
        else:
            return None #Or raise an exception, or return the original string.
    except:
        return None

def extract_page_content(
    page: Page, 
) -> List[Dict[str, str]]:
    
    """lv1 helper function that processes a single parliamentary session and extracts video data.
    Returns list of dictionaries containing video metadata for the session."""
    page_data = []
    try:
        rows = page.query_selector_all('div.mediateka-item')
        print("Found", len(rows), "rows")
        for i, row in enumerate(rows):
            try:
                # Extract the audio URL from the source element
                source_element = row.query_selector('audio source')
                if source_element:
                    mp3_url = source_element.get_attribute('src')
                else:
                    continue
                
                # Extract the date from the span element
                date_element = row.query_selector('span.object-date')
                date_string = date_element.inner_text() if date_element else None
                formatted_date = format_date(date_string) if date_string else None
                
                # Add the data to our results
                page_data.append({
                    "video_id": f"lithuania_{i}_{formatted_date}",
                    "mp3_link": mp3_url,
                })
                
            except Exception as e:
                print(f"Error extracting data from row: {e}")
                continue
    
    except Exception as e:
        print(f"Error extracting audio data: {e}")
        page_data = []

    return page_data

def scrape_parliament_video_data() -> List[Dict[str, str]]:
    """Main function to scrape video data from a parliament website.
    Returns list of dictionaries containing video metadata for all sessions."""
    all_video_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for production
        page = browser.new_page()
        
        try:
            # Process each page
            for page_num in range(1, NUM_PAGES + 1):
                # Navigate to the page
                url = f"https://www.lrs.lt/sip/portal.show?p_r=35826&p_k=1&p5=3&q=seimo&page={page_num}"
                print(f"Processing page {page_num}/{NUM_PAGES}")
                page.goto(url)
                time.sleep(5)  # Allow page to load
                
                try:
                    # Extract content from the current page
                    page_data = extract_page_content(page)
                    all_video_data.extend(page_data)
                    print(f"Extracted {len(page_data)} videos from page {page_num}")
                except Exception as e:
                    print(f"Error processing page {page_num}: {str(e)}")
                
                # Add a small delay between pages to avoid overloading the server
                time.sleep(1)
        except Exception as e:
            print(f"Fatal error in scraping process: {str(e)}")
        finally:
            browser.close()
    
    return all_video_data

if __name__ == "__main__":
    video_data = scrape_parliament_video_data()

    # Save video data to CSV
    with open("scraping-parliaments-internally/lithuania/video_links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "mp3_link", "title"])
        writer.writeheader()
        writer.writerows(video_data)