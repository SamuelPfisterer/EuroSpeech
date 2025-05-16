import csv
import time
import re
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright

# Dictionary of electoral terms to sessions. Each electoral term (except term 4) has sessions from 1 to n.
# We have it in reverse order.
# Term 4 has two sessions: 53 and 54.
ELECTORAL_TERMS_TO_SESSIONS = {
    "9": [str(i) for i in range(32, 0, -1)],
    "8": [str(i) for i in range(104, 0, -1)],
    "7": [str(i) for i in range(58, 0, -1)],
    "6": [str(i) for i in range(61, 0, -1)],
    "5": [str(i) for i in range(29, 0, -1)],
    "4": ["53", "54"]
}

def extract_date_and_subsession(text: str) -> Tuple[str, str]:
    """
    3rd level HELPER function
    Extract date and subsession number from dropdown option text.
    Returns tuple of (formatted_date, subsession_number) or raises Exception if parsing fails.
    """
    date_match = re.search(r',\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    subsession_match = re.match(r"(\d+)", text)
    
    if not date_match or not subsession_match:
        raise Exception(f"Failed to parse date or subsession from text: {text}")
        
    day = date_match.group(1).zfill(2)
    month = date_match.group(2).zfill(2)
    year = date_match.group(3)
    formatted_date = f"{day}{month}{year}"
    
    return formatted_date, subsession_match.group(1)

def process_session(page: Page, term: str, session_num: str) -> List[Dict[str, str]]:
    """
    2nd level HELPER function
    Process a single parliamentary session and extract video data.
    Returns list of dictionaries containing video metadata.
    We use generic_video_link, since download using yt-dlp was possible.
    """
    session_data = []
    session_url = f"https://tv.nrsr.sk/archiv/schodza/{term}/{session_num}"
    print(f"Processing session {session_num} for term {term} at {session_url}")
    
    page.goto(session_url)
    time.sleep(1)  # Short pause after loading

    # Get all options from the dropdown menu
    dropdown_options = page.query_selector_all('select#SelectedDate option')
    
    for option in dropdown_options:
        text = option.inner_text()
        if not text:
            continue
            
        try:
            formatted_date, subsession = extract_date_and_subsession(text)
            
            # Build final URL with display parameters
            subsession_url = f"{session_url}?MeetingDate={formatted_date}&DisplayChairman=true"
            print(f"Processing date: {formatted_date}")
            print(f"Subsession URL: {subsession_url}")

            # Commented out some info, since we dont need (encoded in video_id)
            video_metadata = {
                "video_id": f"slovakia_{term}_{session_num}_{subsession}_{formatted_date}",
                #"term": term,
                #"session": session_num,
                #"subsession": subsession,
                "generic_video_link": subsession_url,
                "html_link": subsession_url,
                "date": formatted_date
            }
            session_data.append(video_metadata)
            
        except Exception as e:
            print(f"Error processing option {text}: {str(e)}")
            continue
            
    return session_data

def scrape_plenary_video_links() -> List[Dict[str, str]]:
    """
    top level function
    Main function to scrape video links from the Slovak Parliament website.
    Returns list of dictionaries containing video metadata for all sessions.
    """
    plenary_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for background execution
        page = browser.new_page()

        # Calculate total number of sessions for progress bar
        total_sessions = sum(len(sessions) for sessions in ELECTORAL_TERMS_TO_SESSIONS.values())
        progress_bar = tqdm(total=total_sessions, desc="Overall progress")

        # Process each electoral term and its sessions
        for term, sessions in ELECTORAL_TERMS_TO_SESSIONS.items():
            try:
                for session_num in sessions:
                    session_data = process_session(page, term, session_num)
                    plenary_data.extend(session_data)
                    progress_bar.update(1)
                    
            except Exception as e:
                print(f"Error processing term {term}: {str(e)}")
                continue

        progress_bar.close()
        browser.close()

    return plenary_data

if __name__ == "__main__":
    data = scrape_plenary_video_links()
    with open("slovakia/streaming_urls.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "generic_video_link", "html_link", "date"])
        writer.writeheader()
        writer.writerows(data)

"""
Creates the required .csv, matching video and transcript links for country Slovakia.
The website structure has the following hierarchy:
- Electoral Term
  - Sessions
    - Subsessions (days)

URL Formats:
- Session URL: https://tv.nrsr.sk/archiv/schodza/{term}/{session_num}
- Subsession URL: https://tv.nrsr.sk/archiv/schodza/{term}/{session_num}?MeetingDate={formatted_date}&DisplayChairman=true

CSV Columns:
- video_id: Unique identifier for the video
- generic_video_link: Link to the video
- processed_transcript_html_link: Link to the processed transcript HTML
- date: Formatted date of the session
"""