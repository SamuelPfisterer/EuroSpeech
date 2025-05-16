import csv
import time
import re
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright

# Dictionary of legislative terms to sessions for keys 11 to 14.
# Each legislative term has sessions from 1 to n, where n is the provided number.
# The sessions are represented as strings in ascending order.
# We want each session to be eactly 3 digits long, if less, we prepend with zeros: "001" is the first session
LEGISLATIVE_TERMS_TO_SESSIONS = {
    "11": [str(i).zfill(3) for i in range(1, 537)],
    "12": [str(i).zfill(3) for i in range(1, 509)],
    "13": [str(i).zfill(3) for i in range(1, 551)],
    "14": [str(i).zfill(3) for i in range(1, 325)]
}

LEGISLATIVE_TERMS_TO_VIDEO_ID = {
    "11": "193290",
    "12": "186993",
    "13": "471276",
    "14": "506899",
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

def get_session_video_data(page: Page, term: str) -> List[Dict[str, str]]:
    """
    2nd level HELPER function
    This function is responsible for processing a parliamentary session
    and extracting relevant video data. It currently does not implement any logic.
    """
    term_url = f"https://parlament.mt/en/menues/reference-material/archives/media-archive/?legislature={LEGISLATIVE_TERMS_TO_VIDEO_ID[term]}"
    print(f"Fetching videos for term {term} at {term_url}")

    page.goto(term_url)
    time.sleep(10)  # Wait for the page to load

    video_data = []

    # Expand Plenary Session section
    page.locator("div.panel-heading:has-text('Plenary Session')").click()
    
    # Wait for ANY MP3 links to exist (not necessarily visible)
    page.wait_for_selector("a[href*='.mp3']", state="attached", timeout=60000)
    
    # Get ALL MP3 links using Angular-friendly selector
    mp3_links = page.eval_on_selector_all(
        "a[ng-href*='.mp3'], a[href*='.mp3']",  # Handle both href and ng-href
        "elements => elements.map(e => e.href || e.getAttribute('ng-href'))"
    )
    
    total_mp3_links = len(mp3_links)  # Count total MP3 links
    print(f"Total MP3 links found: {total_mp3_links}")

    filtered_plenary_links = [
        mp3_link for mp3_link in mp3_links 
        if "plenary" in mp3_link.lower()  # Case-insensitive match
    ]

    print(f"Found {len(filtered_plenary_links)} Plenary Session MP3 links:")
    for mp3_link in filtered_plenary_links:  # Deduplicate again
        # Extract session number using regex
        session_num = re.search(r'Plenary%20(\d{3})', mp3_link).group(1)

        # Extract and reformat date using regex
        date_match = re.search(r'%20(\d{2}-\d{2}-\d{4}|(\d{4})-(\d{2})-(\d{2}))', mp3_link)
        date = date_match.group(1).replace("-", "") if date_match else ""
        if date == "":
            raise Exception(mp3_link)

        video_data.append({
            "video_id": f"{term}_{session_num}_{date}",
            "mp3_link": mp3_link,
        })
    return video_data

def get_session_transcript_data(page: Page, term: str) -> List[Dict[str, str]]:
    term_url = f"https://parlament.mt/mt/{term}th-leg/plenary-session/?type=committeedocuments"
    print(f"Fetching documents for term {term} at {term_url}")
    
    page.goto(term_url)
    time.sleep(10)  # pause after loading, since page needs long to load

    transcript_data = []

    # Get all downloadable Word links that end with "d_par" before the file extension
    word_links = page.query_selector_all('a[href$=".docx"], a[href$=".doc"]')
    word_count = 0  # Initialize a counter for word documents
    for link in word_links:
        word_url = f"https://parlament.mt/{link.get_attribute('href')}"
        url_part_of_interest = word_url.split("/")[-1]
        file_type = url_part_of_interest.split(".")[-1]
        # We only consider word documents that end with "d_par" before the file_extension
        if url_part_of_interest.split(".")[0][-5:] == "d_par" and file_type in ["docx", "doc"]:
            print(f"Found downloadable Word link: {word_url}")
            session_num = url_part_of_interest.split("d_par")[0][-3:]
            date_str = url_part_of_interest.split("_")[0]
            date = f"{date_str[6:8]}{date_str[4:6]}{date_str[0:4]}"
            print(f"Extracted session number: {session_num}, date: {date}")

            if file_type == "docx":
                transcript_data.append({
                    "transcript_id": f"{term}_{session_num}_{date}",
                    "docx_link": word_url,
                    "doc_link": ""
                })
            # else file_type == "doc"
            else:
                transcript_data.append({
                    "transcript_id": f"{term}_{session_num}_{date}",
                    "docx_link": "",
                    "doc_link": word_url
                })

            print(transcript_data[-1])
            word_count += 1  # Increment the counter for each found document

    print(f"Total Word documents found: {word_count}")  # Print the total count of word documents
    return transcript_data

def scrape_plenary_video_links() -> List[Dict[str, str]]:
    """
    top level function
    Main function to scrape video links from the Maltese Parliament website.
    Returns list of dictionaries containing video metadata for all sessions.
    """
    plenary_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for background execution
        page = browser.new_page()


        # Process each electoral term and its sessions
        for term, sessions in tqdm(LEGISLATIVE_TERMS_TO_SESSIONS.items()):
            try:
                #session_video_data = get_session_video_data(page, term)
                session_transcript_data = get_session_transcript_data(page, term)

             
                    

                plenary_data.extend(session_transcript_data)
                    
            except Exception as e:
                print(f"Error processing term {term}: {str(e)}")
                continue

        browser.close()

    return plenary_data

if __name__ == "__main__":
    data = scrape_plenary_video_links()
    with open("transcript_urls.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "doc_link", "docx_link"])
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