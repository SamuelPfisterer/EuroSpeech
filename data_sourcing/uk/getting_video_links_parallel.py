import csv
import time
import re
import os
import logging
from tqdm import tqdm
from typing import List, Dict
from playwright.sync_api import Page, sync_playwright
from datetime import datetime, timedelta
from urllib.parse import quote
from playwright.sync_api import ElementHandle
import multiprocessing

# Configure logging
logging.basicConfig(
    filename='scraping-parliaments-internally/uk/video_scraping_parallel_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Date range for scraping
START_DATE = "01/01/2021"
END_DATE = "30/04/2025"

def extract_date(h5_tags) -> str:
    """Extracts and formats a date from h5 tags containing session start time.
    Args:
        h5_tags: List of h5 elements containing session information
    Returns:
        Formatted date string in ddmmyyyy format
    Raises:
        Exception: If no valid date is found in the h5 tags or if date parsing fails"""
    for h5 in h5_tags:
        text = h5.inner_text().strip()
        if "Start Time:" in text:
            match = re.search(r"(\d{1,2}) (\w+) (\d{4})", text)
            if match:
                day, month_str, year = match.groups()
                try:
                    date_obj = datetime.strptime(f"{day} {month_str} {year}", "%d %B %Y")
                    return date_obj.strftime("%d%m%Y")
                except ValueError:
                    raise Exception("No valid date found in h5 tags")

def extract_location(item_row: ElementHandle) -> str | None:
    """Extracts the location of a parliamentary session from a search result row.
    Args:
        item_row: Playwright ElementHandle representing a search result row
    Returns:
        The location text if found, None if the location cannot be extracted
    Raises:
        AttributeError: If required elements for location extraction are not found"""
    try:
        text_inner = item_row.query_selector(".col-lg-9 .search-text-inner")
        if not text_inner:
            raise AttributeError("Could not find search-text-inner element for session location")

        location_element = text_inner.query_selector("p strong")
        if not location_element:
            raise AttributeError("Could not find location element")

        return location_element.inner_text().strip()
    except Exception as e:
        logging.warning(f"Failed to extract location: {str(e)}")
        return None

def extract_month_video_data(page: Page) -> List[Dict[str, str]]:
    """Extracts video metadata for all parliamentary sessions in a monthly search page.
    Args:
        page: Playwright Page object containing the loaded search page
    Returns:
        List of dictionaries containing video metadata (id, link, location) for the month
    Raises:
        Exception: If video link extraction fails for any session"""
    video_data = []

    search_items = page.query_selector_all(".search-item .row")
    sessions = [item for item in search_items if item.query_selector("a.search-thumb-inner")]

    for i, session in enumerate(sessions):
        try:
            location = extract_location(session)

            # we skip sign language videos since they are duplicate
            if "BSL" in location:
                continue

            href_obj = session.query_selector("a.search-thumb-inner")
            href = href_obj.get_attribute("href")
            h5_tags = session.query_selector_all("h5") #needed for the date
            date = extract_date(h5_tags)

            video_data.append({
                "video_id": f"uk_{i}_{date}",
                "generic_video_link": href,
                "location" : location
            })

            logging.info(video_data[-1])
        except AttributeError:
            raise Exception("Failed to extract video link from search item")

    return video_data

def process_month_url(month_url: str) -> List[Dict[str, str]]:
    """Processes a single month URL to extract video data using Playwright.
    Args:
        month_url: URL of the monthly search page to process
    Returns:
        List of dictionaries containing video metadata for all sessions in the month
    Note:
        Automatically scrolls through the page to load all results before extraction"""
    all_video_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        logging.info(f"Processing month: {month_url} in process {multiprocessing.current_process().name}")
        try:
            page.goto(month_url)
            previous_height = page.evaluate("() => document.body.scrollHeight")

            # Scroll to the bottom to load all results
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                new_height = page.evaluate("() => document.body.scrollHeight")
                if new_height == previous_height:
                    logging.info(f"Scrolled to the end of the page for {month_url}")
                    break
                previous_height = new_height

            all_video_data.extend(extract_month_video_data(page))
        except Exception as e:
            logging.error(f"Error processing {month_url}: {e}")
        finally:
            browser.close()
    return all_video_data

def generate_monthly_urls() -> List[str]:
    """Generates monthly search URLs for parliamentary videos within the specified date range.
    Returns:
        List of URLs for searching parliamentary videos, each URL covering one month
    Note:
        Each URL covers a full month from the first to the last day, with dates URL encoded"""
    base_url = "https://www.parliamentlive.tv/Search?Keywords=&Member=&MemberId=&House=Commons&Business=Chamber"
    urls = []

    # Convert to datetime objects
    current = datetime.strptime(START_DATE, "%d/%m/%Y")
    end = datetime.strptime(END_DATE, "%d/%m/%Y")

    while current <= end:
        # Start date string (always the first of the month)
        start_str = current.strftime("%d/%m/%Y")

        # Calculate the last day of the current month
        if current.month == 12:
            last_day = datetime(current.year, 12, 31)
        else:
            next_month = datetime(current.year, current.month + 1, 1)
            last_day = next_month - timedelta(days=1)
        end_str = last_day.strftime("%d/%m/%Y")

        # URL encode the dates (slashes must become %2F)
        start_encoded = quote(start_str, safe='')
        end_encoded = quote(end_str, safe='')

        url = f"{base_url}&Start={start_encoded}&End={end_encoded}"
        urls.append(url)

        # Move to the first day of the next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return urls

def scrape_parliament_video_data_parallel(all_month_urls: List[str]) -> List[Dict[str, str]]:
    """Scrapes video metadata from ParliamentLive.tv for the specified date range using multiprocessing.
    Args:
        all_month_urls: List of monthly search URLs to process
    Returns:
        List of dictionaries containing video metadata (id, link, location) for all sessions
    Note:
        Uses multiprocessing with a fixed number of cores (4) to process URLs in parallel"""
    all_video_data = []
    num_cores = 4
    logging.info(f"Using {num_cores} cores for multiprocessing.")

    with multiprocessing.Pool(processes=num_cores) as pool:
        results = list(tqdm(pool.imap(process_month_url, all_month_urls), total=len(all_month_urls), desc="Processing months"))
        for result in results:
            all_video_data.extend(result)

    return all_video_data

if __name__ == "__main__":
    all_month_urls = generate_monthly_urls()
    video_data = scrape_parliament_video_data_parallel(all_month_urls)

    # Save video data to CSV
    file_exists = os.path.isfile("scraping-parliaments-internally/uk/video_links.csv")
    with open("scraping-parliaments-internally/uk/video_links.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "generic_video_link", "location"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(video_data)