"""
Slovenian Parliament Video Scraper - Parallel Version

This script is a parallelized version of the Slovenian parliament video scraper.
It uses Python's multiprocessing to distribute the work across different cores.
Each process handles a specific year, starting from December of that year and working backward.

Function Call Tree:
------------------
scrape_parliament_video_data_parallel (Main function)
├── process_year (Worker function for each process)
│   ├── navigate_to_year (Helper function to navigate to specific year)
│   └── navigate_through_calendar (Core function)
│       ├── get_calendar_prefix (Lv 2 Helper)
│       ├── extract_day_sessions (Lv 2 Core function)
│       │   ├── extract_session_info (Lv 3 Helper)
│       └── navigate_to_previous_month (Lv 2 Helper)
└── merge_results (Helper function to combine results from all processes)

Function descriptions:
---------------------
- setup_logging: Configure logging for the script with process-specific log files
- extract_session_info: Extract session number and type from a parliament session element
- extract_day_sessions: Extract all parliament session data from a single day's page
- get_calendar_prefix: Extract the dynamic calendar ID prefix from the page
- navigate_to_previous_month: Navigate to the previous month in the calendar
- navigate_through_calendar: Navigate through calendar months, collect video data
- navigate_to_year: Navigate to a specific year in the calendar
- process_year: Worker function for processing a single year's data
- merge_results: Merge results from all processes into a single CSV file
- scrape_parliament_video_data_parallel: Main entry point for parallel scraping
"""

import csv
import time
import random
import json
import re
import logging
import os
import multiprocessing
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import Page, sync_playwright
from botasaurus.browser import Driver
from botasaurus.browser import browser
from botasaurus.soupify import soupify

# Configure logging
def setup_logging(log_level=logging.INFO, process_id=None):
    """Set up logging configuration for the script."""
    # Get directory of current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create log file path in same directory as script
    if process_id is not None:
        log_file = os.path.join(script_dir, f"scraping_video_links_process_{process_id}.log")
    else:
        log_file = os.path.join(script_dir, "scraping_video_links_parallel.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger(f"slovenia_parliament_scraper_{process_id if process_id else 'main'}")

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

def navigate_to_year(page: Page, target_year: int) -> None:
    """
    Navigate to December of the target year in the calendar.
    Keeps clicking the previous month button until we reach December of the target year.
    
    Args:
        page: Playwright Page object
        target_year: The year to navigate to
    """
    logger.info(f"Navigating to December {target_year}")
    
    while True:
        # Get current month/year from calendar
        month_year_locator = page.locator("td[colspan='5'] span")
        month_year_text = month_year_locator.inner_text()
        logger.info(f"Current calendar display: {month_year_text}")
        
        # Parse current month and year
        try:
            parts = month_year_text.split()
            if len(parts) != 2:
                logger.error(f"Unexpected month/year format: {month_year_text}")
                break
                
            month_sl, year_str = parts
            current_year = int(year_str)
            
            # If we've reached December of our target year, stop
            if current_year == target_year:
                logger.info(f"Reached {target_year}")
                break
            
            # Click the previous month button
            prev_button = page.locator('//div[starts-with(@id, "zabuto_calendar_") and contains(@id, "_nav-prev")]')
            if prev_button.count() > 0:
                prev_button.click()
                
                # Wait for the month text to change
                timeout = 5000  # 5 seconds
                start_time = time.time()
                while True:
                    new_text = page.locator("td[colspan='5'] span").inner_text()
                    if new_text != month_year_text:
                        break
                    
                    if time.time() - start_time > timeout/1000:
                        logger.warning("Timeout waiting for month to change")
                        break
                        
                    time.sleep(0.2)
            else:
                logger.warning("Previous month button not in DOM.")
                break
            
            # Short pause between clicks
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.error(f"Error navigating to year {target_year}: {e}", exc_info=True)
            break

def process_year(year: int) -> List[Dict[str, str]]:
    """
    Worker function for each process.
    Process a specific year completely, navigating to that year in the calendar
    and scraping all video links from that year.
    
    Args:
        year: The year to process
        
    Returns:
        List of dictionaries containing video data
    """
    # Set up process-specific logger
    global logger
    logger = setup_logging(logging.INFO, f"year_{year}")
    logger.info(f"Starting to process year {year}")
    
    # Create target date (January 1st of the year)
    target_date = datetime(year, 1, 1)
    
    logger.info(f"Starting scraping for year {year} with target date: {target_date}")
    
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
        
        # Navigate to the target year
        navigate_to_year(page, year)
        
        # Process all months until target date
        logger.info("Starting calendar navigation")
        video_data = navigate_through_calendar(page, target_date)
        
        logger.info("Closing browser")
        browser.close()
    
    logger.info(f"Scraping complete for year {year}. Found {len(video_data)} videos.")
    
    # Save process-specific results to CSV
    output_path = f"scraping-parliaments-internally/slovenia/video_links_year_{year}.csv"
    logger.info(f"Saving data for year {year} to {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "processed_video_link", "title"])
        writer.writeheader()
        writer.writerows(video_data)
    
    logger.info(f"Data for year {year} saved to {output_path}")
    return video_data

def merge_results(results: List[List[Dict[str, str]]], output_path: str) -> None:
    """
    Merge results from all processes into a single CSV file.
    
    Args:
        results: List of lists of dictionaries containing video data from each process
        output_path: Path to save the merged results
    """
    logger = setup_logging(logging.INFO)
    logger.info("Merging results from all processes")
    
    # Flatten the results
    all_video_data = []
    for process_data in results:
        all_video_data.extend(process_data)
    
    # Save merged results to CSV
    logger.info(f"Saving merged data to {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "processed_video_link", "title"])
        writer.writeheader()
        writer.writerows(all_video_data)
    
    logger.info(f"Merged data saved to {output_path}")

def scrape_parliament_video_data_parallel(start_year: int, end_year: int) -> None:
    """
    Main function - entry point of the parallel script.
    Distribute the scraping work across multiple processes.

    Args:
        start_year: The year to start scraping from
        end_year: The year to stop scraping at
        num_processes: Number of processes to use (defaults to number of CPU cores)
    """
    import multiprocessing
    import logging

    # Set up main logger
    global logger
    logger = setup_logging(logging.INFO)

    num_processes = multiprocessing.cpu_count()

    logger.info(f"Starting parallel scraping with {num_processes} processes")
    logger.info(f"Scraping from {start_year} to {end_year}")

    # Generate one task (year) per process
    tasks = list(range(start_year, end_year - 1, -1))  # inclusive of end_year

    # Create a pool and run the tasks
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_year, tasks)
    
    # Merge the results
    output_path = "scraping-parliaments-internally/slovenia/video_links.csv"
    merge_results(results, output_path)
    
    logger.info("Parallel scraping complete")

if __name__ == "__main__":
    # Set the years to scrape
    start_year = 2025  # Start from the most recent year
    end_year = 1990    # End at the oldest year
    
    # Run the parallel scraper
    scrape_parliament_video_data_parallel(start_year, end_year)
