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

MONTH_MAP = {
    'Jan': '01',
    'Feb': '02',
    'Mar': '03',
    'Apr': '04',
    'May': '05',
    'Jun': '06',
    'Jul': '07',
    'Aug': '08',
    'Sep': '09',
    'Oct': '10',
    'Nov': '11',
    'Dec': '12'
}

def get_session_video_data(page: Page, term: str) -> List[Dict[str, str]]:
    """
    2nd level HELPER function
    This function is responsible for processing a parliamentary session
    and extracting relevant video data.
    """
    # We use the English version of the website, since the maltese has inconsistent naming of "Plenary Session"
    term_url = f"https://parlament.mt/en/menues/reference-material/archives/media-archive/?legislature={LEGISLATIVE_TERMS_TO_VIDEO_ID[term]}"
    print(f"Fetching videos for term {term} at {term_url}")

    page.goto(term_url)
    time.sleep(5)  # Wait for the page to load

    video_data = []

    # Get all panel headings and print their titles
    panel_headings = page.query_selector_all("div.panel-heading")
    print("Available panel titles:")
    for heading in panel_headings:
        title = heading.inner_text()
        print(f"- {title}")

    #TODO This section does not work. The panel is not selected automatically. I cheated by manually opening the first expandable panel.
    #After that, the code works fine.

    # Wait for the Plenary Session section to be visible
    page.wait_for_selector("div.panel-heading:has-text('PLENARY SESSION')", state="visible", timeout=60000)
    
    # Expand Plenary Session section
    page.locator("div.panel-heading:has-text('PLENARY SESSION')").click(timeout=60000)
    
    # Wait for the table to be visible
    page.wait_for_selector("table.table-striped", state="visible", timeout=60000)
    
    # Find all table rows
    rows = page.query_selector_all('table.table-striped tbody tr')
    for row in tqdm(rows):
        try:
            # Extract session number and date from the first column
            session_info = row.query_selector('td:nth-child(1) a').inner_text()
            session_num = session_info.split(' - ')[0]
            date_parts = session_info.split(' - ')[1].split()  # Split "07 May 2022 10:45 am"
            day = date_parts[0].zfill(2)  # Ensure two digits
            month = MONTH_MAP[date_parts[1]]  # Convert month name to number
            year = date_parts[2]
            date = f"{day}{month}{year}"  # Format as ddmmyyyy

            # Find the MP3 link in the second column
            mp3_link_element = row.query_selector('td:nth-child(2) a[href$=".mp3"]')
            if mp3_link_element:
                mp3_link = f"https://parlament.mt{mp3_link_element.get_attribute('href')}"
                # Only add if "plenary" is in the mp3_link (case insensitive)
                if "plenary" in mp3_link.lower():
                    video_data.append({
                        "video_id": f"{term}_{session_num}_{date}",
                        "mp3_link": mp3_link,
                    })
        except Exception as e:
            print(f"Error occurred while processing session info {session_info}: {str(e)}")

    print(f"Found {len(video_data)} Plenary Session MP3 links")
    return video_data

def get_session_transcript_data(page: Page, term: str) -> List[Dict[str, str]]:
    term_url = f"https://parlament.mt/mt/{term}th-leg/plenary-session/?type=committeedocuments"
    print(f"Fetching documents for term {term} at {term_url}")
    
    page.goto(term_url)
    time.sleep(10)  # pause after loading, since page needs long to load

    transcript_data = []

    # Find all table rows
    rows = page.query_selector_all('table.table-striped tbody tr')
    for row in tqdm(rows):
        # Extract session number and date from the first column
        session_info = row.query_selector('td:nth-child(1) a').inner_text()
        session_num = session_info.split(' - ')[0]
        date_str = session_info.split(' - ')[1].split()[0]  # Get '21/06/2022'
        date = date_str.replace('/', '')  # Convert to ddmmyyyy format

        # Find the transcript link in the fourth column
        transcript_link = row.query_selector('td:nth-child(4) a')
        if transcript_link:
            transcript_url = f"https://parlament.mt{transcript_link.get_attribute('href')}"
            file_type = transcript_url.split(".")[-1]

            if file_type == "docx":
                transcript_data.append({
                    "transcript_id": f"{term}_{session_num}_{date}",
                    "docx_link": transcript_url,
                    "doc_link": ""
                })
            elif file_type == "doc":  # file_type == "doc"
                transcript_data.append({
                    "transcript_id": f"{term}_{session_num}_{date}",
                    "docx_link": "",
                    "doc_link": transcript_url
                })
            else:
                print(f"Unknown file type: {file_type}. Skipping...")

    print(f"Total transcript documents found: {len(transcript_data)}")
    return transcript_data

def scrape_plenary_links() -> List[Dict[str, str]]:
    """
    top level function
    Main function to scrape video links from the Maltese Parliament website.
    Returns list of dictionaries containing video metadata for all sessions.
    """
    plenary_video_data = []
    plenary_transcript_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for background execution
        page = browser.new_page()


        # Process each electoral term and its sessions
        for term, sessions in LEGISLATIVE_TERMS_TO_SESSIONS.items():
            try:
                session_video_data = get_session_video_data(page, term)
                session_transcript_data = get_session_transcript_data(page, term)

                plenary_video_data.extend(session_video_data)
                plenary_transcript_data.extend(session_transcript_data)
                    
            except Exception as e:
                print(f"Error processing term {term}: {str(e)}")
                continue

        browser.close()

    return plenary_video_data, plenary_transcript_data

def merge_csv(video_path: str, transcript_path: str, output_path: str) -> None:
    """
    Merge video and transcript CSV files on their ID columns.
    Only keeps rows where transcript_id matches a video_id.
    """
    # Read video data
    with open(video_path, 'r', encoding='utf-8') as f:
        video_reader = csv.DictReader(f)
        video_dict = {row['video_id']: row for row in video_reader}
    
    # Read transcript data and merge
    merged_data = []
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript_reader = csv.DictReader(f)
        for row in transcript_reader:
            video_id = row['transcript_id']
            if video_id in video_dict:
                merged_row = {
                    'video_id': video_id,
                    'mp3_link': video_dict[video_id]['mp3_link'],
                    'docx_link': row['docx_link'],
                    'doc_link': row['doc_link']
                }
                merged_data.append(merged_row)
    
    # Write merged data
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, ['video_id', 'mp3_link', 'docx_link', 'doc_link'])
        writer.writeheader()
        writer.writerows(merged_data)

if __name__ == "__main__":
    video_data, transcript_data = scrape_plenary_links()

    video_out_path = "scraping-parliaments-internally/malta/video_urls.csv"
    transcript_out_path = "scraping-parliaments-internally/malta/transcript_urls.csv"
    merged_out_path = "scraping-parliaments-internally/malta/malta_urls.csv"
    
    with open(video_out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["video_id", "mp3_link"])
        writer.writeheader()
        writer.writerows(video_data)

    with open(transcript_out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "docx_link", "doc_link"])
        writer.writeheader()
        writer.writerows(transcript_data)
    
    # Merge the CSV files
    merge_csv(video_out_path, transcript_out_path, merged_out_path)


"""
Creates the required .csv, matching video and transcript links for country Slovakia.
The website structure has the following hierarchy:
- Electoral Term (11th-14th)
  - Plenary Sessions
    - Audio recordings (MP3)
    - Transcripts (DOC/DOCX)

URL Formats:
- Video Archive URL: https://parlament.mt/en/menues/reference-material/archives/media-archive/?legislature={video_id}
- Transcript URL: https://parlament.mt/mt/{term}th-leg/plenary-session/?type=committeedocuments

CSV Columns:
- video_id: Unique identifier for the session (format: {term}_{session_num}_{date})
- mp3_link: Link to the audio recording in MP3 format
- docx_link: Link to the transcript in DOCX format (if available)
- doc_link: Link to the transcript in DOC format (if available)
"""