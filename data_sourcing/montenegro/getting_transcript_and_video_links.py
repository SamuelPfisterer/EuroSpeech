"""
This script scrapes parliamentary session data from the Montenegrin Parliament website,
including video links and transcript documents. It uses Playwright for web scraping
and outputs the data to a CSV file.

The script handles:
- Scraping session metadata (date, title, links)
- Extracting YouTube video links from session pages
- Extracting transcript links from session pages (just the session page)
- Formatting and saving data to CSV

CSV Output Format:
- video_id: Unique identifier for the session (format: montenegro_{index}_{date}) index is chosen by the order of the sessions on the page
- youtube_link: URL of the YouTube video
- title: Session title
- processed_transcript_html_link: URL of the session page containing transcript
"""

import csv
import time
import re
from tqdm import tqdm
from typing import List, Dict
from playwright.sync_api import Page, sync_playwright

# Mapping of Montenegrin month names to numeric values
MONTH_MAP = {
    'januar': '01',
    'februar': '02',
    'mart': '03',
    'april': '04',
    'maj': '05',
    'jun': '06',
    'jul': '07',
    'avgust': '08',
    'septembar': '09',
    'oktobar': '10',
    'novembar': '11',
    'decembar': '12'
}

def get_youtube_link(browser, url: str) -> str:
    """
    Helper function that extracts YouTube video link from a session page.
    
    Args:
        browser: Playwright browser instance
        url: URL of the session page to scrape
        
    Returns:
        YouTube video URL or None if not found
    """
    # Create a new context and page
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(url)
        time.sleep(2)  # Wait for page to load

        # Wait for the YouTube iframe to load
        page.wait_for_selector("iframe[src*='youtube.com']")
        
        # Extract the YouTube video URL from the iframe src attribute
        yt_link = page.eval_on_selector(
            "iframe[src*='youtube.com']",
            "element => element.src"
        )
        
        # Clean up the URL to get just the video ID
        if "embed/" in yt_link:
            yt_link = f"https://www.youtube.com/watch?v={yt_link.split('embed/')[1].split('?')[0]}"
        
        print("Found YouTube video:", yt_link)
        return yt_link
    except Exception as e:
        print(f"Exception occurred while processing {url}: {str(e)}")
        return None
    finally:
        # Close the context when done
        context.close()

def scrape_plenary_links() -> List[Dict[str, str]]:
    """
    Main function to scrape video links and session metadata from the Montenegrin Parliament website.
    
    Returns:
        List of dictionaries containing session metadata:
        - video_id: Unique identifier (format: montenegro_{index}_{date})
        - youtube_link: URL of the YouTube video
        - title: Session title
        - processed_transcript_html_link: URL of the session page
    """
    plenary_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True for background execution
        page = browser.new_page()

        try:
            # Load the main page containing session listings
            page.goto("https://www.skupstina.me/en/chronology-of-discussions")
            time.sleep(3)
            
            # Load all content by clicking "Load more" until it disappears
            while True:
                try:
                    print("Loading more content...")
                    load_more_button = page.locator('span:has-text("Load more")')
                    if not load_more_button.is_visible():
                        break
                        
                    load_more_button.click()
                    time.sleep(2)
                except Exception as e:
                    print(f"Error loading more content: {str(e)}")
                    break

            # Process all session rows
            rows = page.locator('div.ui-post-item')
            total_rows = rows.count()
            print(f"Total rows loaded: {total_rows}")

            for i in tqdm(range(total_rows), desc="Processing sessions", unit="session"):
                try:
                    row = rows.nth(i)
                    
                    # Extract and format date
                    date_time = row.locator('time.text-14').inner_text()
                    day, month, year, _ = date_time.replace('.', '').split()
                    date = f"{day.zfill(2)}{MONTH_MAP[month]}{year}"
                    
                    # Extract session title
                    title = row.locator('h4.font-serif').inner_text()
                    
                    # Extract and normalize session link
                    session_link = row.locator('a[ui-sref]').get_attribute('href')
                    if not session_link.startswith(('http://', 'https://')):
                        session_link = f"https://www.skupstina.me{session_link}"
                    
                    # Get YouTube video link
                    yt_link = get_youtube_link(browser, session_link)

                    plenary_data.append({
                        "video_id": f"montenegro_{i+1}_{date}",
                        "youtube_link": yt_link,
                        "title": title,
                        "processed_transcript_html_link": session_link,
                    })
                    
                except Exception as e:
                    print(f"Error processing row {i}: {str(e)}")

        except Exception as e:
            print(f"Error processing data: {str(e)}")

        browser.close()
    return plenary_data

if __name__ == "__main__":
    # Scrape data and save to CSV
    data = scrape_plenary_links()
    out_path = "scraping-parliaments-internally/montenegro/montenegro_urls.csv"
    
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "youtube_link", "title", "processed_transcript_html_link"])
        writer.writeheader()
        writer.writerows(data)