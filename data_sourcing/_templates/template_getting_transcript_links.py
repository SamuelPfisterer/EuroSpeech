import csv
import time
import re
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright

# Global dictionary mapping terms to sessions
TERMS_TO_SESSIONS = {
    # Define your terms and sessions here
    # Example:
    # "9": [str(i) for i in range(32, 0, -1)],
    # "8": [str(i) for i in range(104, 0, -1)],
}

def extract_date(text: str) -> str:
    """lv2 helper function that extracts and formats a date from a given text string.
    Returns formatted date string in ddmmyyyy format."""
    # Implement date extraction logic here
    pass

def extract_transcript_link(page: Page) -> str:
    """lv2 helper function that extracts the transcript link from a given page.
    Returns the transcript URL string."""
    # Implement transcript link extraction logic here
    pass

def extract_session_title(page: Page) -> str:
    """lv2 helper function that extracts the session title from a given page.
    Returns the title string."""
    # Implement session title extraction logic here
    pass

def process_transcript_session(page: Page, term: str, session_num: str) -> List[Dict[str, str]]:
    """lv1 helper function that processes a single parliamentary session and extracts transcript data.
    Returns list of dictionaries containing transcript metadata for the session."""
    session_data = []
    session_url = f"..."  # Replace with the actual URL format
    print(f"Processing transcript session {session_num} for term {term} at {session_url}")
    page.goto(session_url)
    time.sleep(1) #allow page to load.

    try:
        date = extract_date(...)
        transcript_link = extract_transcript_link(page)
        title = extract_session_title(page)
        transcript_id = f"{term}_{session_num}_{date}"

        session_data.append({
            "transcript_id": transcript_id,
            "transcript_link": transcript_link,
            "title": title,
        })
    except Exception as e:
        print(f"Error processing transcript session {session_num}: {e}")

    return session_data

def scrape_parliament_transcript_data() -> List[Dict[str, str]]:
    """Main function to scrape transcript data from a parliament website.
    Returns list of dictionaries containing transcript metadata for all sessions."""
    all_transcript_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for production
        page = browser.new_page()

        total_sessions = sum(len(sessions) for sessions in TERMS_TO_SESSIONS.values())
        progress_bar = tqdm(total=total_sessions, desc="Transcript progress")

        for term, sessions in TERMS_TO_SESSIONS.items():
            for session_num in sessions:
                session_data = process_transcript_session(page, term, session_num)
                all_transcript_data.extend(session_data)
                progress_bar.update(1)

        progress_bar.close()
        browser.close()

    return all_transcript_data

if __name__ == "__main__":
    transcript_data = scrape_parliament_transcript_data()

    # Save transcript data to CSV
    with open("parliament_transcript_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "transcript_link", "title"])
        writer.writeheader()
        writer.writerows(transcript_data)