"""
This script scrapes parliamentary session data from the Serbian Parliament website's HTML archives,
including video links and session metadata. It uses Playwright for web scraping
and outputs the data to a CSV file.

The script handles:
- Navigating through different convocation periods (2012, 2014, 2016, 2020)
- Extracting session metadata (date, title)
- Extracting MP4 video links
- Formatting and saving data to CSV

CSV Output Format:
- video_id: Unique identifier for the session (format: serbia_{convocation}_{index}_{date})
- video_link: URL of the MP4 video
- title: Session title
- date: Session date
"""

import csv
import time
import re
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict
from playwright.sync_api import Page, sync_playwright

# Convocation periods and their URLs (2024 excluded as archive is empty)
CONVOCATIONS = {
    "2012": "https://www.videonet.co.rs/nsrsArhiva1Z.htm?reload0.5370919472409829",
    "2014": "https://www.videonet.co.rs/nsrsArhiva2Z.htm?reload0.2860772935070174",
    "2016": "https://www.videonet.co.rs/nsrsArhiva11Z.htm?reload0.3563297809885144",
    "2020": "https://www.videonet.co.rs/nsrsArhiva12Z.htm?reload0.0774563845717745",
    "2024": "https://www.videonet.co.rs/nsrsArhiva14Z.htm?reload0.6143956522488926"
}

def extract_date_from_title(title: str) -> str:
    """
    Extract and format date from session title.
    
    Args:
        title: Session title containing date
        
    Returns:
        Formatted date string (DDMMYYYY)
    """
    # Extract date using regex (looking for DD.MM.YYYY format)
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', title)
    if date_match:
        day, month, year = date_match.groups()
        return f"{day}{month}{year}"
    return None

def scrape_video_links() -> List[Dict[str, str]]:
    """
    Main function to scrape video links and session metadata from the Serbian Parliament website.
    
    Returns:
        List of dictionaries containing session metadata:
        - video_id: Unique identifier
        - video_link: URL of the MP4 video
        - title: Session title
        - date: Session date
    """
    plenary_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True for production
        
        for convocation, url in CONVOCATIONS.items():
            print(f"Processing convocation {convocation}")
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Navigate to the convocation page
                page.goto(url)
                time.sleep(2)
                
                # Find all paragraphs containing MP4 links
                rows = page.query_selector_all('p:has(a[href*=".mp4"])')
                print(len(rows))
                for idx, row in tqdm(enumerate(rows), total=len(rows), desc=f"Processing convocation {convocation}"):
                    try:
                        # Extract title (all text before the links)
                        title = row.inner_text().split('(')[0].strip()
                        
                        # Extract MP4 link
                        mp4_link = row.query_selector('a[href*=".mp4"]')
                        video_link = mp4_link.get_attribute('href') if mp4_link else None
                        
                        # Extract date from title
                        date = extract_date_from_title(title) if title else None

                        
                        if title and video_link and date:
                            # Create unique video_id
                            video_id = f"serbia_{convocation}_{idx}_{date}"
                            
                            plenary_data.append({
                                "video_id": video_id,
                                "mp4_video_link": video_link,
                                "title": title,
                            })
                            #print(plenary_data[-1])
                            
                    except Exception as e:
                        print(f"Error processing row in convocation {convocation}: {str(e)}")
                        continue
                
            except Exception as e:
                print(f"Error processing convocation {convocation}: {str(e)}")
            finally:
                context.close()
                
        browser.close()
    return plenary_data

if __name__ == "__main__":
    # Scrape data and save to CSV
    data = scrape_video_links()
    out_path = "scraping-parliaments-internally/serbia/serbia_video_links.csv"
    
    # Open CSV file for writing with UTF-8 encoding
    # Create a DictWriter with specified fieldnames
    # Write header row followed by all data rows
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "mp4_video_link", "title"])
        writer.writeheader()
        writer.writerows(data)
