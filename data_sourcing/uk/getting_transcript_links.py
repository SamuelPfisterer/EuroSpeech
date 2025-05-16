import csv
import time
import random
import re
import logging
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright
from datetime import datetime, timedelta
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from urllib.parse import urljoin
import os

# Configure logging
logging.basicConfig(
    filename='scraping-parliaments-internally/uk/transcript_scraping_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

START_DATE = "2007-12-01"
PDF_START_DATE = "2015-05-01"
END_DATE = "2010-01-01"


def extract_date(text: str) -> str:
    """lv2 helper function that extracts and formats a date from a given text string.
    Returns formatted date string in ddmmyyyy format."""
    # Split URL by '/' and get the last part which is the date
    date_str = text.split('/')[-1]
    
    # Convert from yyyy-mm-dd to ddmmyyyy format
    year, month, day = date_str.split('-')
    return f"{day}{month}{year}"


@browser(reuse_driver=True, headless=True)
def extract_transcripts_of_day(driver: Driver, url : str) -> List[Dict[str, str]]:
    transcript_data = []

    driver.get(url)
    
    time.sleep(random.uniform(4, 5))
    soup = soupify(driver)

    time.sleep(random.uniform(1, 2))

    
    try:
        outer_blocks = soup.find_all('div', class_='d-none d-lg-block')
        for block in outer_blocks:
            inner_block = block.find('div', class_='widget')
    
            if inner_block:   
                date_str = url.split('/')[-1]
                date = extract_date(url)

                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                pdf_start_date_obj = datetime.strptime(PDF_START_DATE, '%Y-%m-%d').date()
                pdf_link = f"https://hansard.parliament.uk/pdf/commons/{date_str}" if date_obj >= pdf_start_date_obj else None

                dropdown_menu = soup.find('div', class_='dropdown-menu')

                if dropdown_menu:
                    # Find all the dropdown item links (<a> tags with class 'dropdown-item')
                    dropdown_items = dropdown_menu.find_all('a', class_='dropdown-item')
                    for item in dropdown_items:
                        i = 0
                        link = item['href']

                        # We only want html link, not pdf
                        if not "html" in link:
                            continue

                        location = link.split("/")[-1]

                        if location == "CommonsChamber" or location == "WestminsterHall":
                            location_url = f"https://hansard.parliament.uk/html/commons/{date_str}/{location}"

                            transcript_data.append({
                                "transcript_id": f"uk_{i}_{date}",
                                "pdf_link": pdf_link,
                                "location_link": location_url,
                                "location": location,
                             })
                            i += 1

                    logging.info(transcript_data[-i:])

                break # We break out of the outer for loop once we found the first block with a widget
        else:
            logging.info("No transcripts found for this date.")
    except AttributeError as e:
        logging.error(f"Failed to find transcript links in the page structure: {str(e)}")

    return transcript_data

def scrape_parliament_transcript_data() -> List[Dict[str, str]]:
    """Main function to scrape transcript data from a parliament website.
    Returns list of dictionaries containing transcript metadata for all sessions."""
    all_transcript_data = []

    url = "https://hansard.parliament.uk/commons/"


    # 1. Convert date strings to datetime objects
    try:
        start_date = datetime.strptime(START_DATE, '%Y-%m-%d').date()
        end_date = datetime.strptime(END_DATE, '%Y-%m-%d').date()
    except ValueError:
        logging.error("Error: Invalid date format. Please use 'yyyy-mm-dd'.")
        return all_transcript_data
    
    # 2. Generate a list of dates within the range
    current_date = start_date
    date_list = []
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    # 3. Iterate through the list of dates and construct URLs

    for i, date_obj in enumerate(tqdm(date_list, desc="Dates")):
        date_str = date_obj.strftime('%Y-%m-%d')
        date_url = url + date_str
        logging.info(f"Navigating to: {date_url}")

        # 4. Simulate visiting the page (replace with actual scraping later)
        all_transcript_data.extend(extract_transcripts_of_day(date_url))

    return all_transcript_data

if __name__ == "__main__":
    transcript_data = scrape_parliament_transcript_data()

    # Save transcript data to CSV, appending to existing file
    file_exists = os.path.isfile("scraping-parliaments-internally/uk/transcript_links_temp.csv")
    with open("scraping-parliaments-internally/uk/transcript_links_temp.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "pdf_link", "location_link", "location"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(transcript_data)