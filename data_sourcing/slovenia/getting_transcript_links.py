import csv
import time
import re
import logging
from tqdm import tqdm
from tqdm.auto import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright
from urllib.parse import urljoin

"""
Slovenian Parliament Transcript Scraper

This script scrapes transcript links from the Slovenian Parliament website.
It navigates through different parliamentary terms, extracts session information,
and collects links to parliamentary session transcripts.

Function Hierarchy:
------------------
scrape_parliament_transcript_data()
├── navigate_through_pages(term)
│   └── process_transcript_session(term, session_link)
│       └── extract_session_info()
│       └── extract_date()

Helper Functions:
- extract_date(title): Extracts and formats date from a string
- extract_session_info(page): Extracts session title, sessionnumber, and sessiontype from a page
- process_transcript_session(page, term, session_link): Processes a single parliamentary session
- navigate_through_pages(page, term): Navigates through all pages of a term
- scrape_parliament_transcript_data(): Main function that orchestrates the scraping process
"""

def extract_date(title: str) -> str:
    """Helper function to extract date from a string and format it as ddmmyyyy."""
    match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", title)
    if match:
        day = match.group(1).zfill(2)
        month = match.group(2).zfill(2)
        year = match.group(3)
        return f"{day}{month}{year}"
    else:
        raise ValueError(f"No date found in title: {title}")

def extract_session_info(page: Page) -> str:
    """lv2 helper function that extracts the session title from a given page.
    Returns the title string."""
    session_title = page.locator('span[id="viewns_Z7_J9KAJKG10OK070QT45U8J900J1_:form1:txtIzbranElement"] h2').text_content()
    
    parts = session_title.split()
    session_number = int(parts[0].replace(".", ""))
    session_type = parts[1]
    
    return session_title, session_number, session_type

def process_transcript_session(page: Page, term: str, session_link: str) -> List[Dict[str, str]]:
    """lv1 helper function that processes a single parliamentary session and extracts transcript data.
    Returns list of dictionaries containing transcript metadata for the session."""
    session_data = []

    try:
        # Navigate to the session link
        page.goto(session_link)
        time.sleep(2)
        # Find all anchor tags containing "Zapis seje" in their text
        transcript_elements = page.locator('a:has-text("Zapis seje")').all()
        session_title, session_type, session_num = extract_session_info(page)

        logging.info(f"Found {len(transcript_elements)} transcript elements")

        for i, element in enumerate(transcript_elements):
            href = element.get_attribute("href")
            anchor_text = element.inner_text() #text displayed of the href

            # Make the URL absolute if it's relative
            transcript_link = urljoin(page.url, href)
            # Extract date from the title or link if possible
            date = extract_date(anchor_text)

            session_data.append({
                "transcript_id": f"slovenia_{term}_{session_type}_{session_num}_{i}_{date}",
                "processed_transcript_text_link": transcript_link,
                "title": session_title,
            })
            logging.info(f"Created session data {session_data[-1]}")

    except Exception as e:
        logging.error(f"Error processing transcript session at {session_link}: {e}")
    finally:
        # Go back to previous page in both success and error cases
        page.go_back()
        time.sleep(1)

    return session_data

def navigate_through_pages(page: Page, term: str) -> List[Dict[str, str]]:
    """Function that navigates through all pages of a term and processes each session.
    Returns list of dictionaries containing transcript metadata for all sessions."""
    page_data = []
    logging.info(f"Navigating through pages for term {term}")
    time.sleep(2)  # Allow page to load
    
    # Get total number of pages
    page_info_element = page.locator('text=/Page \d+ of \d+/')
    page_info_text = page_info_element.text_content()

    # Step 2: Extract the last number (Y) using regex
    total_pages = int(re.search(r'\d+$', page_info_text).group())
    logging.info(f"Total pages: {total_pages}")
    
    # Process each page
    for page_num in tqdm(range(1, total_pages + 1), desc=f"Processing pages for term {term}"):
        logging.info(f"Processing page {page_num} of {total_pages}")
        
        # Extract session rows from current page
        session_rows = page.locator("td[nowrap='true'][valign='top'] a.underline")
        for i in range(session_rows.count()):
            session_title = session_rows.nth(i).inner_text()
            session_link = session_rows.nth(i).get_attribute("href")
            logging.info(f"Found session: {session_title}")
            
            # Create a full URL if the link is relative
            if session_link and not session_link.startswith("http"):
                session_link = urljoin(page.url, session_link)
            
            # Process each session
            session_data = process_transcript_session(page, term, session_link)
            page_data.extend(session_data)
        
        # Navigate to next page if not on the last page
        if page_num < total_pages:
            page.locator('input.pagerDeluxeActive_button[alt="Next"]').click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)  # Allow page to load
    
    return page_data

def scrape_parliament_transcript_data() -> List[Dict[str, str]]:
    """Main function to scrape transcript data from a parliament website.
    Returns list of dictionaries containing transcript metadata for all sessions.
    It selects a term and then calls the navigate_through_pages function to navigate through all pages of a term
    """
    transcript_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # set headless=True for production
        page = browser.new_page()
        page.goto("https://www.dz-rs.si/wps/portal/Home/seje/sejeDZ/poDatumu/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8zivSy9Hb283Q0NDIxCXAwCQ_zdjM3cPY0DLc30wwkpiAJKG-AAjgbo-t2NgkwNAl2MnHyDDYwNgoONwPoJ2o_HAgL6I4H6zREK_L0NzIEKTExDLbwsDQyA9gfrR_rrR6oaBBoEFDuCrcOrvCA3NDSiKkQ30FFREQAdyxpD/#Z7_J9KAJKG10OK070QT45U8J900S2")
        time.sleep(2)
        dropdown = page.locator('select[id*="menu1"]')


        options = dropdown.locator('option').all()
        search_button = page.locator('input[value="Išči seje"]')

        for index, option in tqdm(enumerate(options), desc="Processing terms"):
            # We only get the first 3 terms as the rest do not have videos 
            # Videos are only 2015 and 2020-2025
            if index > 2:
                continue
            # Select dropdown option
            option_text = option.text_content().strip()
            dropdown.select_option(index=index)
            
            # Extract start year
            date_part = option_text.split('(')[1].split(')')[0]
            start_year = date_part.split('-')[0].strip().split('.')[-1].strip()

            logging.info(f"Selected term: {option_text} ({start_year})")
            
            # Click search button and wait for navigation
            with page.expect_navigation():
                search_button.click()

            term_data = navigate_through_pages(page, start_year)
            transcript_data.extend(term_data)

        browser.close()

    return transcript_data

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraping-parliaments-internally/slovenia/scraping.log'),
            logging.StreamHandler()
        ]
    )
    
    transcript_data = scrape_parliament_transcript_data()

    # Save transcript data to CSV
    with open("scraping-parliaments-internally/slovenia/transcript_links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "processed_transcript_text_link", "title"])
        writer.writeheader()
        writer.writerows(transcript_data)