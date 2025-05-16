import csv
import time
import re
import logging
from tqdm import tqdm
from typing import List, Tuple, Dict
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.browser import Wait
from playwright.sync_api import Page, sync_playwright

"""
This script has been split into two separate scripts:

1. `extract_transcript_page_html.py`: Navigates to the Kosovo Parliament website, clicks the "Show More" 
   button until all sessions are loaded, and saves the loaded HTML to a file.

2. `extract_transcript_row_data.py`: Reads the saved HTML file, processes each row to extract transcript 
   metadata, generates unique transcript IDs, and saves the collected data to a CSV file.

Please refer to the respective scripts for more details on their functionality.
"""

# Configure logging to write to a file in the same directory
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='transcript_scraper.log',
    filemode='w'
)

# Map month names to numbers (assuming Albanian month names)
MONTH_MAP = {
    'Janar': '01', 'Shkurt': '02', 'Mars': '03', 'Prill': '04',
    'Maj': '05', 'Qershor': '06', 'Korrik': '07', 'Gusht': '08',
    'Shtator': '09', 'Tetor': '10', 'Nëntor': '11', 'Dhjetor': '12'
}

def extract_date(date_container, relative_link: str) -> str:
    """lv2 helper function that extracts and formats a date from a given date container element.
    Returns formatted date string in ddmmyyyy format."""
    day_span = date_container.find('span', class_='nr')
    month_time_span = date_container.find('span', class_='date-time')
    
    if not (day_span and month_time_span):
        return None
        
    day = day_span.text.strip().zfill(2)
    month_time = month_time_span.text.strip()
    month_name = month_time.split(' ')[0]
    month = MONTH_MAP.get(month_name)
    
    if not month:
        return None

    # Extract year from the link
    year_match = re.search(r'(\d{4})_', relative_link)
    if not year_match:
        return None
        
    year = year_match.group(1)
    return f"{day}{month}{year}"

@browser(reuse_driver=False, headless=False)
def scrape_parliament_transcript_data(driver: Driver, url: str) -> List[Dict[str, str]]:
    """
    Main function to scrape transcript data from the Kosovo Parliament website.
    
    This function performs the following steps:
    1. Navigates to the provided URL
    2. Clicks "Show More" button until all sessions are loaded
    3. Extracts transcript metadata from each session row
    4. Generates unique transcript IDs and collects download links
    
    Args:
        driver: Selenium WebDriver instance
        url: URL of the parliament sessions page
    
    Returns:
        List[Dict[str, str]]: List of dictionaries containing transcript metadata
        Each dictionary has 'transcript_id' and 'transcript_link' keys
    """

    driver.get(url)
    
    time.sleep(10)
    soup = soupify(driver)

    transcript_data = []

    # Load all rows by clicking the button
    while True:
        try:
            show_more_button = driver.select("#js-sessions-show-more")
            is_visible = show_more_button.run_js("""
                (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                        style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        style.opacity !== '0' &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                }
            """)
            if is_visible:
                show_more_button.click()
                logging.info("Clicked on 'TREGO MË SHUMË' button.")
                time.sleep(1)
            else:
                logging.info("The 'Load More' button is no longer visible. Proceeding to scrape data.")
                break
        except Exception as e:
            logging.error(f"An error occurred while trying to click 'Load More': {str(e)}")
            break

    # Extract and save HTML after loading all content
    page_html = soup.html
    with open("scraping-parliaments-internally/kosovo/loaded_transcript_page.html", "w", encoding="utf-8") as f:
        f.write(page_html)
    logging.info("Saved full page HTML to loaded_page.html")

    time.sleep(100)
    logging.info("Finding all rows...")
    items = soup.find_all('div', class_='item')
    rows = []
    for item in items:
        row = item.find('div', class_='row', recursive=False)
        if row:
            rows.append(row)
    logging.info(f"Found {len(rows)} rows. Starting to process rows...")
    
    for i, row in tqdm(enumerate(rows), total=len(rows), desc="Processing rows"):
        date_container = row.find('div', class_='date-container')
        if not date_container:
            logging.warning("No date. Skipping this row.")
            continue

        transcript_link_tag = date_container.find('a', class_='file-icon', string='Transkript')

        if transcript_link_tag:
            relative_link = transcript_link_tag['href']
            absolute_link = "https://www.kuvendikosoves.org" + relative_link

            formatted_date = extract_date(date_container, relative_link)
            if formatted_date:
                transcript_data.append({
                    'transcript_id': f"kosovo_{i}_{formatted_date}",
                    'transcript_link': absolute_link
                })
                logging.info(transcript_data[-1])
        else:
            logging.warning(f"No transcript link found for row {i}.")

    return transcript_data

if __name__ == "__main__":
    url = "https://www.kuvendikosoves.org/shq/seancat/seancat/"

    transcript_data = scrape_parliament_transcript_data(url)

    # Save transcript data to CSV
    with open("parliament_transcript_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "transcript_link"])
        writer.writeheader()
        writer.writerows(transcript_data)