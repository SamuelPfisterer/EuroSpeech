"""
Slovenian Parliament Video Scraper

This script scrapes video links from the Slovenian parliament website, navigating through
the calendar interface to extract videos of parliamentary sessions.

It processes each month's calendar, identifies days with parliament events, and extracts
video links for each session, saving the results to a CSV file.

Function Call Tree:
------------------
scrape_parliament_video_data (Main function)
└── navigate_through_calendar (Core function)
    ├── get_calendar_prefix (Lv 2 Helper)
    ├── extract_day_sessions (Lv 2 Core function)
    │   ├── extract_session_info (Lv 3 Helper)
    │   └── extract_m3u8_url (Lv 3 External API)
    └── navigate_to_previous_month (Lv 2 Helper)

The tree shows the hierarchical relationship between functions:
- Main function: scrape_parliament_video_data
- Core navigation function: navigate_through_calendar
- Helper functions: get_calendar_prefix, navigate_to_previous_month
- Data extraction functions: extract_day_sessions, extract_session_info, extract_m3u8_url
"""

import csv
import time
import random
import json
import re
import logging
import os
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import Page, sync_playwright
from botasaurus.browser import Driver
from botasaurus.browser import browser
from botasaurus.soupify import soupify

# Configure logging
def setup_logging(log_level=logging.INFO):
    """Set up logging configuration for the script."""
    # Get directory of current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create log file path in same directory as script
    log_file = os.path.join(script_dir, "scraping_video_links.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger("slovenia_parliament_scraper")

# Initialize logger
logger = setup_logging()

# Define the base URL for the Slovenian parliament website
BASE_URL = "https://www.dz-rs.si/wps/portal/Home/deloDZ/seje/sejeDt"

# Define a mapping of Slovenian month names to English month names
MONTH_NAMES = {
    "januar": "January",
    "februar": "February",
    "marec": "March",
    "april": "April",
    "maj": "May",
    "junij": "June",
    "julij": "July",
    "avgust": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "december": "December"
}

def extract_session_info(session) -> Dict[str, str]:
    """
    Lv 3 Helper function used by extract_day_sessions.
    Extract session number and type from a parliament session element.
    
    Args:
        session: A Playwright ElementHandle representing a session row
        
    Returns:
        Dict containing session_number, session_type, and full_text
    """
    session_number = ""
    session_type = ""
    full_text = ""
    
    try:
        number_element = session.query_selector('span.flSejeNumber')
        if number_element:
            full_text = number_element.inner_text().strip().strip('()')
            
            # Split the text to separate number and type
            parts = full_text.split('. ', 1)
            if len(parts) > 0:
                session_number = parts[0]
                if len(parts) > 1:
                    session_type = parts[1]
            
            logger.info(f"Extracted session number:{session_number}, type: {session_type}")
    except Exception as e:
        logger.error(f"Error extracting session info: {e}", exc_info=True)
    
    return {
        "session_number": session_number,
        "session_type": session_type,
        "full_text": full_text
    }

# @browser(reuse_driver=False, headless=False)
# def extract_m3u8_url(driver: Driver, url: str) -> Optional[str]:
#     """
#     Lv 3 External API function used by extract_day_sessions.
#     Extract m3u8 URL from a webpage using Botasaurus.
    
#     Args:
#         driver: Botasaurus driver instance
#         url: URL of the webpage containing the video
        
#     Returns:
#         The extracted m3u8 URL if found, None otherwise
#     """
#     logger.info(f"Botasaurus: Starting extraction of m3u8 URL from {url}")
#     try:
#         # Navigate to the URL
#         logger.info(f"Botasaurus: Navigating to {url}")
#         driver.get(url)
#         wait_time = random.randint(5, 7)
#         logger.debug(f"Botasaurus: Waiting {wait_time} seconds for page to load")
#         time.sleep(wait_time)
        
#         # Get initial page content
#         logger.info("Botasaurus: Getting page content with soupify")
#         soup = soupify(driver)
#         time.sleep(2)
        
#         # Look for the JSON-LD script tag
#         logger.debug("Botasaurus: Searching for JSON-LD script tag")
#         script_tag = soup.find('script', {'type': 'application/ld+json', 'id': '__jw-ld-json'})
#         if script_tag:
#             logger.debug("Botasaurus: Found JSON-LD script tag, parsing content")
#             data = json.loads(script_tag.string)
#             m3u8_url = data.get("contentUrl")
#             if m3u8_url:
#                 logger.info(f"Botasaurus: Successfully found m3u8 link: {m3u8_url}")
#             else:
#                 logger.warning("Botasaurus: JSON-LD found but no contentUrl in data")
#             return m3u8_url
#         else:
#             logger.warning("Botasaurus: No JSON-LD script tag with m3u8 link found")
#             raise Exception("No JSON-LD script tag with m3u8 link found")
#     except Exception as e:
#         logger.error(f"Botasaurus: An error occurred: {e}", exc_info=True)
#         return None

def extract_day_sessions(page: Page, session_date: str) -> List[Dict[str, str]]:
    """
    Lv 2 Core function used by navigate_through_calendar.
    Extract all parliament session data from a single day's page.
    
    Args:
        page: Playwright Page object
        session_date: Date string in YYYY-MM-DD format
        
    Returns:
        List of dictionaries containing video data
    """
    day_data = []
    logger.info(f"Processing session date: {session_date}")
    
    try:
        # Find all parliament sessions on this date
        sessions = page.query_selector_all('li.ui-dataview-row')
        logger.debug(f"Found {len(sessions)} sessions for date {session_date}")
        
        # Process each session
        for session in sessions:
            try:
                # Only process Državni zbor sessions
                title_element = session.query_selector('span.flLbl:has-text("Državni zbor")')
                if title_element:
                    # Extract session number and type
                    session_info = extract_session_info(session)
                    session_number = session_info["session_number"]
                    session_type = session_info["session_type"]
                    full_text = session_info["full_text"]
                    
                    # Find all video links in this session
                    video_links = session.query_selector_all('a[href*="rtvslo.si/embed/"]')
                    logger.debug(f"Found {len(video_links)} video links for session {full_text}")

                    date_obj = datetime.strptime(session_date, "%Y-%m-%d")
                    date = date_obj.strftime("%d%m%Y")

                    for i, video_link in enumerate(video_links):
                        video_url = video_link.get_attribute('href')
                        if video_url:
                            logger.info(f"Found video website: {video_url}")
                            
                            video_id = f"slovenia_{session_number}_{session_type}_{i}_{date}"
                            logger.info(f"Extracting m3u8 URL for video ID: {video_id}")
                            #m3u8_link = extract_m3u8_url(video_url)
                            
                            # Add to session data
                            day_data.append({
                                "video_id": video_id,
                                "processed_video_link": video_url,
                                "title": f"Državni zbor ({full_text})"
                            })
                            logger.info(f"Added video data: {day_data[-1]}")
                        else:
                            logger.warning(f"No video link found for session {full_text}")
            except Exception as e:
                logger.error(f"Error processing session: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Error extracting data for date {session_date}: {e}", exc_info=True)
    
    logger.info(f"Extracted {len(day_data)} videos for date {session_date}")
    return day_data

def get_calendar_prefix(page: Page) -> Optional[str]:
    """
    Lv 2 Helper function used by navigate_through_calendar.
    Extract the dynamic calendar ID prefix from the page.
    
    Args:
        page: Playwright Page object
        
    Returns:
        The calendar prefix if found, None otherwise
    """
    calendar_prefix = None
    try:
        calendar_day = page.locator('td[id^="zabuto_calendar_"]').first
        if calendar_day:
            day_id = calendar_day.get_attribute('id')
            if day_id:
                match = re.search(r'zabuto_calendar_([^_]+)', day_id)
                if match:
                    calendar_prefix = match.group(1)
    except Exception as e:
        logger.error(f"Error finding calendar prefix: {e}", exc_info=True)
    
    return calendar_prefix

def navigate_to_previous_month(page: Page, current_month_text: str) -> bool:
    """
    Lv 2 Helper function used by navigate_through_calendar.
    Navigate to the previous month in the calendar.
    
    Args:
        page: Playwright Page object
        current_month_text: The current month/year text for comparison
        
    Returns:
        True if navigation was successful, False otherwise
    """
    try:
        prev_button = page.locator('//div[starts-with(@id, "zabuto_calendar_") and contains(@id, "_nav-prev")]')
        
        if prev_button.count() > 0:
            prev_button.click()
            
            # Wait for the month text to change
            timeout = 5000  # 5 seconds
            start_time = time.time()
            while True:
                new_text = page.locator("td[colspan='5'] span").inner_text()
                if new_text != current_month_text:
                    return True
                
                if time.time() - start_time > timeout/1000:
                    logger.warning("Timeout waiting for month to change")
                    return False
                    
                time.sleep(0.2)
        else:
            logger.warning("Previous month button not in DOM.")
            return False
    except Exception as e:
        logger.error(f"Error clicking previous month button: {e}", exc_info=True)
        return False

def navigate_through_calendar(page: Page, target_date: datetime) -> List[Dict[str, str]]:
    """
    Core function used by scrape_parliament_video_data.
    Navigate through calendar months, click on each day with events, and collect data
    until reaching the target date.
    
    Args:
        page: Playwright Page object
        target_date: Datetime object representing the target end date
        
    Returns:
        List of dictionaries containing all video data
    """
    video_data = []
    
    while True:
        # Get current month/year from calendar
        month_year_locator = page.locator("td[colspan='5'] span")
        month_year_text = month_year_locator.inner_text()
        logger.info(f"\nCurrent calendar display: {month_year_text}")
        
        # Parse Slovenian month and year
        try:
            parts = month_year_text.split()
            if len(parts) == 2:
                month_sl, year = parts
                if month_sl.lower() in MONTH_NAMES:
                    month_en = MONTH_NAMES[month_sl.lower()]
                    current_date = datetime.strptime(f"{month_en} {year}", "%B %Y")
                else:
                    logger.error(f"Unknown month name: {month_sl}")
                    break
            else:
                logger.error(f"Unexpected month/year format: {month_year_text}")
                break
        except Exception as e:
            logger.error(f"Error parsing date: {e}", exc_info=True)
            break
        
        # Get the calendar ID prefix for locating calendar elements
        calendar_prefix = get_calendar_prefix(page)
        
        # Find all date cells in calendar
        if not calendar_prefix:
            logger.warning("Using generic selector for date cells")
            date_cells = page.locator('//td[starts-with(@id, "zabuto_calendar_")]').all()
        else:
            date_cells = page.locator(f'td[id^="zabuto_calendar_{calendar_prefix}_"]').all()
        
        # Process each date cell
        for date_cell in date_cells:
            try:
                date_id = date_cell.get_attribute("id")
                class_attr = date_cell.get_attribute("class") or ""
                
                # Skip dates from other months
                if "noCurrentMonth" in class_attr:
                    continue
                    
                # Only process days with events
                if "event-styled" in class_attr:
                    # Click the date to view the session details
                    date_cell.click()
                    wait_time = random.uniform(2, 4)
                    logger.debug(f"Waiting {wait_time:.2f} seconds after clicking date")
                    time.sleep(wait_time)
                    
                    # Extract date from ID (format: zabuto_calendar_XXXX_YYYY-MM-DD)
                    session_date = date_id.split('_')[-1]
                    
                    # Extract session data for this day
                    day_data = extract_day_sessions(page, session_date)
                    logger.info("-"*80)
                    video_data.extend(day_data)
                    
            except Exception as e:
                logger.error(f"Error processing date: {e}", exc_info=True)
                
            # Short pause between processing days
            time.sleep(random.uniform(0.5, 1))
        
        # Check if we've reached or passed the target date
        if current_date <= target_date:
            logger.info(f"Reached or passed target date: {target_date}")
            break
        
        # Navigate to previous month
        if not navigate_to_previous_month(page, month_year_text):
            break
            
        time.sleep(random.uniform(1, 2))
    
    return video_data

def scrape_parliament_video_data(target_date_str: str) -> List[Dict[str, str]]:
    """
    Main function - entry point of the script.
    Scrape video data from the Slovenian parliament website.
    
    Args:
        target_date_str: Target end date in YYYY-MM-DD format
        
    Returns:
        List of dictionaries containing video data
    """
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    logger.info(f"Starting scraping with target date: {target_date}")
    
    with sync_playwright() as p:
        logger.info("Launching browser")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the main page and wait for load
        logger.info(f"Navigating to {BASE_URL}")
        page.goto(BASE_URL)
        wait_time = random.uniform(2, 5)
        logger.debug(f"Waiting {wait_time:.2f} seconds for page to load")
        time.sleep(wait_time)
        
        # Process all months until target date
        logger.info("Starting calendar navigation")
        video_data = navigate_through_calendar(page, target_date)
        
        logger.info("Closing browser")
        browser.close()
    
    logger.info(f"Scraping complete. Found {len(video_data)} videos.")
    return video_data

if __name__ == "__main__":
    # Set this to the oldest date you want to scrape (the script will stop once it reaches this date)
    target_date = "1990-05-01"
    
    # Run the scraper
    logger.info(f"Starting Slovenian Parliament video scraper, will collect data until {target_date}")
    video_data = scrape_parliament_video_data(target_date)
    logger.info(f"Scraping complete. Found {len(video_data)} videos.")
    
    # Save video data to CSV
    output_path = "scraping-parliaments-internally/slovenia/video_links.csv"
    logger.info(f"Saving data to {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "processed_video_link", "title"])
        writer.writeheader()
        writer.writerows(video_data)
    
    logger.info(f"Data saved to {output_path}")
