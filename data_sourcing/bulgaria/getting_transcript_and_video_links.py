import re
import csv
import logging
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urljoin
from tqdm import tqdm
import os

"""
Bulgarian Parliament Transcript and Video Scraper

This script scrapes transcript and video links from the Bulgarian Parliament website.
It navigates through different years and months, extracts session information,
and collects links to parliamentary session transcripts and associated videos.

Function Hierarchy:
------------------
click_all_months_in_range_and_extract_links(url, start_year, end_year)
├── extract_session_data(page, session_url)
│   └── extract_video_data(page, date)

Helper Functions:
- extract_video_data(page, date): Extracts video links from a parliamentary session page
- extract_session_data(page, session_url): Extracts title, date, and calls extract_video_data
- click_all_months_in_range_and_extract_links(url, start_year, end_year): Main function that orchestrates the scraping process
"""

def extract_video_data(page, date : str):
    """
    Extracts video data from the page.
    """
    video_data = []
    print(f"Processing date: {date}")

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
        else:
            error_msg = f"No .mp4 link found or src attribute missing after clicking button '{button_text}'."
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    return video_data

def extract_session_data(page, session_url):
    """
    Navigates to the link URL, extracts the title and date,
    calls extract_data, and returns the modified list of dictionaries.
    """
    session_data = []
    print(f"Processing session: {session_url}")
    try:
        page.goto(session_url)
        time.sleep(3)
        # Locate the container with the title and date
        title_date_container = page.locator('div.mb-3').first

        # Extract the title from the h2 tag
        title_element = title_date_container.locator('h2')
        title = title_element.inner_text().strip()

        # Extract the date text
        date_text_element = title_date_container.inner_text()
        # Use regex to find the date in dd/mm/yyyy format
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text_element)

        if date_match:
            day = date_match.group(1)
            month = date_match.group(2)
            year = date_match.group(3)
            date = f"{day}{month}{year}"
        else:
            error_msg = f"Could not extract date from: {date_text_element}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)

        # Here we extract the transcript and video data from the current session
        if date and title:
            video_data = extract_video_data(page, date)

            # Extend the video data with the transcript data
            for item in video_data:
                item["title"] = title
                item["transcript_id"] = f"bulgaria_{date}"
                item['process_transcript_link'] = session_url
                session_data.append(item)
        else:
            error_msg = f"Could not extract title or date from: {session_url}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)

        return session_data

    except Exception as e:
        error_msg = f"An error occurred while processing link: {session_url} - {e}"
        print(f"Error: {error_msg}")
        raise Exception(error_msg)

def click_all_months_in_range_and_extract_links(url, start_year, end_year):
    """
    Main function that orchestrates the scraping process.
    Navigates through years and months in the specified range,
    extracts session links, and processes each session.
    """
    data = []
    total_links = 0
    print(f"Starting scraping for years {start_year} to {end_year}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        time.sleep(7)
        # Locate all year containers
        year_containers = page.locator('.row.p-archive-list > div.col-12')

        # Iterate through each year container
        for year_container in tqdm(year_containers.all()):
            try:
                # Extract the year
                year_element = year_container.locator('.archive-head')
                year_text = year_element.inner_text().strip()

                try:
                    year = int(year_text)
                    # Check if the year is within the desired range
                    if start_year <= year <= end_year:
                        print(f"Processing year: {year}")

                        # Locate all month elements within the current year container
                        month_elements = year_container.locator('ul > li > span')

                        # Iterate through each month and click
                        for month_element in month_elements.all():
                            month_text = month_element.inner_text().strip()
                            print(f"Processing month: {month_text}")
                            month_element.click()
                            time.sleep(1)
                            # Wait for the section with links to appear
                            page.wait_for_selector('#period-title', state='visible')

                            # Locate the links within the newly appeared section
                            link_container = page.locator('#period-title ul.p-common-list')
                            links = link_container.locator('li > a')
                            total_links += links.count()
                            
                            # First loop: Collect all session URLs
                            session_urls = []
                            for link in links.all():
                                session_url = urljoin(page.url, link.get_attribute('href'))
                                session_urls.append(session_url)
                            
                            # Second loop: Process each session URL
                            for session_url in session_urls:
                                session_data = extract_session_data(page, session_url)
                                data.extend(session_data)
                            
                            print(f"Finished processing month: {month_text}")
                    else:
                        print(f"Skipping year {year} (outside range {start_year}-{end_year})")
                        #break

                except ValueError:
                    print(f"Error: Could not parse year: {year_text}")

            except Exception as e:
                print(f"Error: An error occurred while processing a year: {e}")

        browser.close()
    print(f"Scraping completed. Total items collected: {len(data)} out of potential {total_links}")
    return data

if __name__ == '__main__':
    website_url = "https://parliament.bg/bg/plenaryst"
    start_year = 2010
    end_year = 2021
    print(f"Starting Bulgarian Parliament scraper for years {start_year}-{end_year}")
    
    data = click_all_months_in_range_and_extract_links(website_url, start_year, end_year)
    print(f"Finished clicking all months for years between {start_year} and {end_year}.")

    # Check if file exists to determine if we need to write header
    file_exists = os.path.exists("scraping-parliaments-internally/bulgaria/bulgaria_urls_sequential.csv")
    
    with open("scraping-parliaments-internally/bulgaria/bulgaria_urls_sequential.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "mp4_link", "title", "transcript_id", "process_transcript_link"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)
    print("Data appended to bulgaria_urls_sequential.csv")

