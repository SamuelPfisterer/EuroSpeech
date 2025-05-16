import csv
import time
import re
from tqdm import tqdm
from typing import List, Tuple, Dict
from playwright.sync_api import Page, sync_playwright


def extract_date(text: str) -> str:
    """Extract and format a date from a given text string.
    Returns formatted date string in DDMMYYYY format."""
    # Look for date pattern in format YYYY-MM-DD
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if match:
        year, month, day = match.groups()
        # Ensure leading zeros for single-digit days/months
        day = f"{int(day):02d}"
        month = f"{int(month):02d}"
        return f"{day}{month}{year}"
    return ""

def extract_session_title(page: Page) -> str:
    """lv2 helper function that extracts the session title from a given page.
    Returns the title string."""
    # Implement session title extraction logic here
    try:
        # Example of a more specific selector or xpath. Must be changed to match actual webpage.

        title_element = page.query_selector(".title")

        if title_element:
            return title_element.inner_text()
        else:
            return ""

    except Exception as e:
        print(f"Error extracting session title: {e}")
        return ""

def process_transcript_session(
    page: Page, 
    term: str, 
    sitting_type: str, 
    sitting_num: str, 
    session_url: str,
    i: str
) -> List[Dict[str, str]]:

    session_data = []
    failed_sessions = []
    failure_reason = ""
    
    try:
        print(f"Navigating to session: {session_url}")
        page.goto(session_url)
        time.sleep(2) #allow page to load.
        
        session_title = extract_session_title(page)
        if not session_title:
            failure_reason = "No session title found"
            failed_sessions.append((session_url, failure_reason))
            print(f"FAILED: {session_url} - {failure_reason}")
            return session_data
            
        session_date = extract_date(session_title)
        if not session_date:
            failure_reason = "No date found in session title"
            failed_sessions.append((session_url, failure_reason))
            print(f"FAILED: {session_url} - {failure_reason}")
            return session_data
        
        # Find the stenograma link
        stenograma_link = None
        potential_links = page.query_selector_all('li.rubrika.with-icon a.link.color-primary')
        
        for link in potential_links:
            if link.inner_text().strip() == "Stenograma":
                stenograma_link = link.get_attribute('href')
                break
        
        if stenograma_link:
            print(f"Found stenograma link: {stenograma_link}")
            page.goto(stenograma_link)
            time.sleep(2)  # Allow page to load
            
            # Extract the word document links
            doc_link = None
            docx_link = None
            
            # Look for DOCX format
            docx_element = page.query_selector('a[href*="/format/MSO2010_DOCX/"]')
            if docx_element:
                docx_link = docx_element.get_attribute('href')
                # Convert to absolute URL if it's a relative URL
                if docx_link and docx_link.startswith('/'):
                    # Extract base URL from current page URL
                    base_url = '/'.join(page.url.split('/')[:3])  # Gets http(s)://domain.com
                    docx_link = base_url + docx_link
                    print(f"Found DOCX link: {docx_link}")
            
            # Look for DOC format
            doc_element = page.query_selector('a[href*="/format/MSO2010_DOC/"]')
            if doc_element:
                doc_link = doc_element.get_attribute('href')
                # Convert to absolute URL if it's a relative URL
                if doc_link and doc_link.startswith('/'):
                    # Extract base URL from current page URL
                    base_url = '/'.join(page.url.split('/')[:3])  # Gets http(s)://domain.com
                    doc_link = base_url + doc_link
                    print(f"Found DOC link: {doc_link}")
            
            if not doc_link and not docx_link:
                failure_reason = "No Word document links found"
                failed_sessions.append((session_url, failure_reason))
                print(f"FAILED: {session_url} - {failure_reason}")
                return session_data
                
            transcript_id = f"lithuania_{term}_{sitting_type}_{sitting_num}_{i}_{session_date}"
            
            session_data.append({
                "transcript_id": transcript_id,
                "doc_link": doc_link if doc_link else "",
                "docx_link": docx_link if docx_link else "",
                "title": session_title,
            })
        else:
            failure_reason = "No stenograma link found"
            failed_sessions.append((session_url, failure_reason))
            print(f"FAILED: {session_url} - {failure_reason}")
    except Exception as e:
        failure_reason = f"Error processing session: {str(e)}"
        failed_sessions.append((session_url, failure_reason))
        print(f"FAILED: {session_url} - {failure_reason}")
                
    return session_data

def process_transcript_sitting(
    page: Page, 
    term: str, 
    sitting_type: str, 
    sitting_num: str, 
    sitting_url: str
) -> List[Dict[str, str]]:
    """lv1 helper function that processes a single parliamentary session and extracts transcript data.
    Returns list of dictionaries containing transcript metadata for the session."""
    sitting_data = []
    failed_sessions = []
    
    try:
        page.goto(sitting_url)
        time.sleep(1) #allow page to load.

        # Extract all session links first
        # Get all table rows (tr elements) that contain session data
        rows = page.query_selector_all('table.tbl-default tbody tr:not(:first-child)')

        session_urls = []
        # Iterate through the rows (each row is a date, meaning it can contain multiple sessions)
        for row in rows:        
             # Extract session links, which are all found in the second column
            session_links_elements = row.query_selector_all('td:nth-child(2) a')
            for session_link in session_links_elements:
                session_url = session_link.get_attribute('href')
                session_urls.append(session_url)
        
        if not session_urls:
            print(f"FAILED: {sitting_url} - No session URLs found")
            
        #Iterate through each link in the session_links list
        for i, session_url in enumerate(session_urls):
            session_data = process_transcript_session(page, term, sitting_type, sitting_num, session_url, i)
            sitting_data.extend(session_data)
    except Exception as e:
        print(f"FAILED: {sitting_url} - Error processing sitting: {str(e)}")
    
    # For now, just return the session links data without processing individual sessions
    return sitting_data

def scrape_parliament_transcript_data() -> List[Dict[str, str]]:
    """Main function to scrape transcript data from a parliament website.
    Returns list of dictionaries containing transcript metadata for all sessions."""
    transcript_data = []
    failed_sittings = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set headless=True for production
        page = browser.new_page()
        
        try:
            # Navigate to the main page with the navigation panel
            page.goto("https://www.lrs.lt/sip/portal.show?p_r=35727&p_k=1&p_a=sale_ses_pos&p_kade_id=10&p_ses_id=140")
            time.sleep(2)  # Allow page to load
            
            # Extract all term elements
            term_elements = page.query_selector_all('li.kade-dropdown')
            total_sittings = 0
            term_sittings = {}
            
            # First collect all sitting URLs organized by term
            print(f"Found {len(term_elements)} term elements to process")
            for term_element in term_elements:
                # Extract term title and first year
                term_title = term_element.query_selector('a.toggler_kade').get_attribute('title')
                
                # Extract the first year from titles like "2024–2028 metų kadencija"
                year_match = re.search(r'(\d{4})–\d{4}', term_title)
                if year_match:
                    term_year = year_match.group(1)  # Get the first year (e.g., "2024")
                    print(term_year)
                else:
                    print(f"FAILED: Could not extract year from term title: {term_title}")
                    continue

                # Extract all sitting links for this term
                sitting_links = []
                sitting_elements = term_element.query_selector_all('li.sesija a.sesija')
                
                for sitting_element in sitting_elements:
                    sitting_url = sitting_element.get_attribute('href')
                    sitting_title = sitting_element.get_attribute('title')
                    sitting_links.append((sitting_url, sitting_title))
                
                term_sittings[term_year] = sitting_links
                total_sittings += len(sitting_links)
            
            # Process all sittings with a progress bar
            print(total_sittings)
            progress_bar = tqdm(total=total_sittings, desc="Video progress")

            for term_year, sittings in term_sittings.items():
                for sitting_url, sitting_title in sittings:
                    try:
                        # Extract sitting number from title (e.g., "9 eilinė" or "4 neeilinė")
                        sitting_match = re.search(r'(\d+)\s+(eilinė|neeilinė)', sitting_title)
                        if sitting_match:
                            sitting_num = sitting_match.group(1)
                            sitting_type = sitting_match.group(2)
                            
                            # Navigate to the sitting page
                            page.goto(sitting_url)
                            time.sleep(1)  # Allow page to load
                            
                            # Process this sitting and get video data
                            # Use the term_year as the term parameter
                            sitting_data = process_transcript_sitting(page, term_year, sitting_type, sitting_num, sitting_url)
                            transcript_data.extend(sitting_data)
                        else:
                            print(f"FAILED: Could not extract sitting number and type from title: {sitting_title}")
                            failed_sittings.append((sitting_url, f"Invalid sitting title format: {sitting_title}"))
                    except Exception as e:
                        print(f"FAILED: Error processing sitting {sitting_url}: {str(e)}")
                        failed_sittings.append((sitting_url, str(e)))
                        
                    progress_bar.update(1)
            
            progress_bar.close()
        except Exception as e:
            print(f"FAILED: Fatal error in scraping process: {str(e)}")
        finally:
            browser.close()
    
    # Log all failed sittings to a file
    with open("scraping-parliaments-internally/lithuania/failed_sessions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Failure Reason"])
        writer.writerows(failed_sittings)
    
    return transcript_data
if __name__ == "__main__":
    transcript_data = scrape_parliament_transcript_data()

    # Save transcript data to CSV
    with open("scraping-parliaments-internally/lithuania/transcript_urls.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["transcript_id", "doc_link", "docx_link", "title"])
        writer.writeheader()
        writer.writerows(transcript_data)