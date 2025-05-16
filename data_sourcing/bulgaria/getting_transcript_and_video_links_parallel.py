import re
import csv
import logging
import multiprocessing
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urljoin
from tqdm import tqdm
import os
from functools import partial

"""
Bulgarian Parliament Transcript and Video Scraper (Parallel Version)

This script scrapes transcript and video links from the Bulgarian Parliament website.
It navigates through different years and months, extracts session information,
and collects links to parliamentary session transcripts and associated videos.
This version uses multiprocessing to parallelize scraping across different years.

Function Hierarchy:
------------------
scrape_with_multiprocessing(url, start_year, end_year, processes)
├── process_year_range(url, year_start, year_end)
│   └── scrape_year(url, year)
│       └── extract_session_data(page, session_url)
│           └── extract_video_data(page, date)

Helper Functions:
- extract_video_data(page, date): Extracts video links from a parliamentary session page
- extract_session_data(page, session_url): Extracts title, date, and calls extract_video_data
- scrape_year(url, year): Scrapes a single year's data
- process_year_range(url, year_start, year_end): Processes a range of years
- scrape_with_multiprocessing(url, start_year, end_year, processes): Divides work and manages multiprocessing
"""

def extract_video_data(page, date : str):
    """
    Extracts video data from the page.
    """
    video_data = []
    logging.info(f"Extracting video data for date: {date}")

    # Locate the container with the video section
    video_section_container = page.locator('div[data-v-bc557e8c][data-v-2b456b1e]')
    # Locate all buttons within the container
    buttons = video_section_container.locator('div.mt-3 > button')

    # Locate the video player
    video_player_container = video_section_container.locator('div.video-player')

    # Iterate through each button and extract the mp4 link
    for i in range(buttons.count()):
        button = buttons.nth(i)
        button_text = button.inner_text().strip()
        logging.info(f"  Clicking button: '{button_text}'")
        button.click()
        # Wait for the video player source to potentially update
        page.wait_for_selector('div.video-player video[src*=".mp4"]', state='attached', timeout=5000)

        # Locate the video tag and extract the src attribute
        video_element = video_player_container.locator('video')
        video_src = video_element.get_attribute('src')

        if video_src and video_src.endswith('.mp4'):
            video_data.append({
                "video_id": f"bulgaria_{i}_{date}", 
                "mp4_link": video_src
                })
            logging.info(f"  Found video with ID: bulgaria_{i}_{date}")
        else:
            error_msg = f"No .mp4 link found or src attribute missing after clicking button '{button_text}'."
            logging.error(error_msg)
            raise Exception(error_msg)
    return video_data

def extract_session_data(page, session_url):
    """
    Navigates to the link URL, extracts the title and date,
    calls extract_data, and returns the modified list of dictionaries.
    """
    session_data = []
    logging.info(f"Extracting session data from URL: {session_url}")
    try:
        page.goto(session_url)
        time.sleep(5)
        # Locate the container with the title and date
        # It should be the first one with div.mb-3 in it
        title_date_container = page.locator('div.mb-3').first

        # Extract the title from the h2 tag
        title_element = title_date_container.locator('h2')
        title = title_element.inner_text().strip()
        logging.info(f"  Extracted title: {title}")

        # Extract the date text
        date_text_element = title_date_container.inner_text()
        # Use regex to find the date in dd/mm/yyyy format
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text_element)

        if date_match:
            day = date_match.group(1)
            month = date_match.group(2)
            year = date_match.group(3)
            date = f"{day}{month}{year}"
            logging.info(f"  Extracted date: {date}")
        else:
            error_msg = f"Could not extract date from: {date_text_element}"
            logging.error(error_msg)
            raise Exception(error_msg)

        # Here we extract the transcript and video data from the current session
        if date and title:
            video_data = extract_video_data(page, date)

            # Extend the video data with the transcript data
            for item in video_data:
                item["title"] = title
                item["transcript_id"] = f"bulgaria_{date}"
                item['process_transcript_link'] = session_url
                print(item)
                session_data.append(item)
            logging.info(f"  Added {len(video_data)} items to session_data")
        else:
            error_msg = f"Could not extract title or date from: {session_url}"
            logging.error(error_msg)
            raise Exception(error_msg)

        return session_data

    except Exception as e:
        error_msg = f"An error occurred while processing link: {session_url} - {e}"
        logging.error(error_msg)
        raise Exception(error_msg)

def scrape_year(url, target_year):
    """
    Scrapes data for a specific year.
    
    Args:
        url (str): The base URL of the Bulgarian parliament website
        target_year (int): The year to scrape
        
    Returns:
        list: A list of dictionaries containing transcript and video data for the year
    """
    process_id = os.getpid()
    year_data = []
    logging.info(f"Process {process_id}: Starting to scrape year {target_year}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        time.sleep(10)
        
        # Locate all year containers
        year_containers = page.locator('.row.p-archive-list > div.col-12')
        logging.info(f"Process {process_id}: Found {year_containers.count()} year containers")

        # Find the container for our target year
        target_year_container = None
        for year_container in year_containers.all():
            try:
                year_element = year_container.locator('.archive-head')
                year_text = year_element.inner_text().strip()
                
                try:
                    year = int(year_text)
                    if year == target_year:
                        target_year_container = year_container
                        logging.info(f"Process {process_id}: Found container for year {target_year}")
                        break
                except ValueError:
                    logging.error(f"Process {process_id}: Could not parse year: {year_text}")
            except Exception as e:
                logging.error(f"Process {process_id}: Error processing year container: {e}")
        
        if not target_year_container:
            logging.error(f"Process {process_id}: Could not find container for year {target_year}")
            browser.close()
            return []
        
        # Process the target year
        try:
            # Locate all month elements within the year container
            month_elements = target_year_container.locator('ul > li > span')
            logging.info(f"Process {process_id}: Found {month_elements.count()} months for year {target_year}")

            # Iterate through each month and click
            for month_element in month_elements.all():
                month_text = month_element.inner_text().strip()
                logging.info(f"Process {process_id}: Clicking month: {month_text}")
                month_element.click()
                time.sleep(1)
                # Wait for the section with links to appear
                page.wait_for_selector('#period-title', state='visible')

                # Locate the links within the newly appeared section
                link_container = page.locator('#period-title ul.p-common-list')
                links = link_container.locator('li > a')

                logging.info(f"Process {process_id}: Found {links.count()} session links for {month_text} {target_year}")
                
                # First loop: Collect all session URLs
                session_urls = []
                for link in links.all():
                    session_url = urljoin(page.url, link.get_attribute('href'))
                    session_urls.append(session_url)
                    logging.debug(f"Process {process_id}: Collected link: {session_url}")
                
                # Second loop: Process each session URL
                for session_url in session_urls:
                    logging.info(f"Process {process_id}: Processing session: {session_url}")
                    session_data = extract_session_data(page, session_url)
                    logging.info(f"Process {process_id}: Finished processing session: {session_url}")
                    year_data.extend(session_data)
                
                logging.info(f"Process {process_id}: Finished processing month: {month_text}")
        
        except Exception as e:
            logging.error(f"Process {process_id}: An error occurred while processing year {target_year}: {e}")
        
        browser.close()
    
    logging.info(f"Process {process_id}: Completed scraping for year {target_year}. Items collected: {len(year_data)}")
    return year_data

def process_year_range(url, years):
    """
    Process a range of years and return the combined data.
    
    Args:
        url (str): The base URL of the Bulgarian parliament website
        years (list): List of years to process
        
    Returns:
        list: Combined data from all years
    """
    process_id = os.getpid()
    logging.info(f"Process {process_id}: Starting to process years {years}")
    
    all_data = []
    for year in years:
        year_data = scrape_year(url, year)
        all_data.extend(year_data)
    
    logging.info(f"Process {process_id}: Finished processing years {years}. Total items: {len(all_data)}")
    return all_data

def scrape_with_multiprocessing(url, start_year, end_year, processes=None):
    """
    Distribute scraping work across multiple processes.
    
    Args:
        url (str): The base URL of the Bulgarian parliament website
        start_year (int): The starting year to scrape
        end_year (int): The ending year to scrape
        processes (int, optional): Number of processes to use. Defaults to CPU count.
        
    Returns:
        list: Combined data from all processes
    """
    if processes is None:
        processes = multiprocessing.cpu_count()
    
    # Make sure we don't create more processes than years
    years_to_scrape = list(range(start_year, end_year + 1))
    processes = min(processes, len(years_to_scrape))
    
    logging.info(f"Starting multiprocessing scraper with {processes} processes for years {start_year}-{end_year}")
    
    # Divide years among processes
    years_per_process = []
    for i in range(processes):
        # Calculate which years this process will handle
        start_idx = i * len(years_to_scrape) // processes
        end_idx = (i + 1) * len(years_to_scrape) // processes
        years_per_process.append(years_to_scrape[start_idx:end_idx])
    
    # Log the division of work
    for i, years in enumerate(years_per_process):
        logging.info(f"Process {i} will handle years: {years}")
    
    # Create a pool and map the work
    with multiprocessing.Pool(processes) as pool:
        process_func = partial(process_year_range, url)
        results = pool.map(process_func, years_per_process)
    
    # Combine results from all processes
    all_data = []
    for result in results:
        all_data.extend(result)
    
    logging.info(f"Multiprocessing completed. Total items collected: {len(all_data)}")
    return all_data

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(process)d - %(message)s',
        handlers=[
            logging.FileHandler('scraping-parliaments-internally/bulgaria/scraping_parallel.log'),
            logging.StreamHandler()
        ]
    )
    
    website_url = "https://parliament.bg/bg/plenaryst"
    start_year = 2010
    end_year = 2025
    processes = 4  # Adjust this number based on your system capabilities
    
    logging.info(f"Starting Bulgarian Parliament parallel scraper for years {start_year}-{end_year} with {processes} processes")
    
    data = scrape_with_multiprocessing(website_url, start_year, end_year, processes)
    logging.info(f"Finished scraping all years between {start_year} and {end_year}. Total items: {len(data)}")

    with open("scraping-parliaments-internally/bulgaria/bulgaria_urls_parallel.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "mp4_link", "title", "transcript_id", "process_transcript_link"])
        writer.writeheader()
        writer.writerows(data)
    logging.info("Data saved to bulgaria_urls_parallel.csv")

