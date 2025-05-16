from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
from tqdm import tqdm

def get_session_data(page, page_number):
    url = f"https://www.hellenicparliament.gr/Praktika/Synedriaseis-Olomeleias?search=off&pageNo={page_number}"
    print(f"\nFetching URL: {url}")
    
    # Navigate to the page
    response = page.goto(url)
    print(f"Response status: {response.status}")
    
    # Wait for the table to be visible
    page.wait_for_selector('table.grid', timeout=10000)
    
    # Get the page content
    soup = BeautifulSoup(page.content(), 'html.parser')
    
    # First check if we can find the table
    table = soup.find('table', class_='grid')
    if not table:
        print("No table with class 'grid' found on page")
        # Debug table structure
        print("\nTable structure:")
        print(f"Number of <table> tags: {len(soup.find_all('table'))}")
        if soup.find_all('table'):
            print("Classes on found tables:")
            for t in soup.find_all('table'):
                print(f"  - {t.get('class', [])}")
        print("\nFirst 500 characters of HTML:")
        print(soup.prettify()[:500])
        return []
        
    # Debug table structure
    print("\nTable structure:")
    print(f"Number of <tr> tags: {len(table.find_all('tr'))}")
    print(f"Number of <th> tags: {len(table.find_all('th'))}")
    print(f"Classes on table: {table.get('class', [])}")
    
    # Find all rows in the table (excluding header)
    rows = table.select('tr:not(.superheader):not(:has(th))')
    print(f"Found table with {len(rows)} total rows")
    
    sessions = []
    for i, row in enumerate(rows):
        # Skip footer rows
        if 'tablefooter' in row.get('class', []):
            print(f"Skipping footer row {i}")
            continue
            
        cols = row.find_all('td')
        if not cols:
            print(f"No columns found in row {i}")
            continue
            
        try:
            date = cols[0].text.strip()
            period = cols[1].text.strip()
            session_type = cols[2].text.strip()
            meeting = cols[3].text.strip()
            
            # Get video links
            video_links = [a['href'] for a in cols[4].find_all('a')]
            video_links = ';'.join(video_links) if video_links else ''
            
            # Get PDF link (if exists)
            pdf_link = ''
            if cols[5].find('a'):
                pdf_link = cols[5].find('a')['href']
                
            # Get DOCX link (if exists)
            docx_link = ''
            if cols[6].find('a'):
                docx_link = cols[6].find('a')['href']
                
            session = {
                'date': date,
                'period': period,
                'session_type': session_type,
                'meeting': meeting,
                'video_links': video_links,
                'pdf_link': pdf_link,
                'docx_link': docx_link
            }
            
            print(f"\nProcessed row {i}:")
            print(f"  Date: {date}")
            print(f"  Meeting: {meeting}")
            print(f"  Video links: {len(video_links.split(';')) if video_links else 0} found")
            print(f"  PDF: {'Yes' if pdf_link else 'No'}")
            print(f"  DOCX: {'Yes' if docx_link else 'No'}")
            
            sessions.append(session)
            
        except Exception as e:
            print(f"\nError processing row {i}:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Row content:")
            print(row.prettify())
            continue
    
    return sessions

def parse_date(date_str):
    try:
        # Remove any text in parentheses and extra whitespace
        cleaned_date = date_str.split('(')[0].strip()
        return datetime.strptime(cleaned_date, '%d/%m/%Y')
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def main():
    page_number = 1
    cutoff_year = 2010
    max_pages = 614
    
    with sync_playwright() as p:
        # Configure browser with stealth settings
        browser = p.chromium.launch(
            headless=False,  # Set to True for production
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )
        
        # Add stealth scripts
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()
        
        with tqdm(total=max_pages, desc="Scraping pages") as pbar:
            with open('session_links.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'period', 'session_type', 'meeting', 
                                                     'video_links', 'pdf_link', 'docx_link'])
                writer.writeheader()
                
                while page_number <= max_pages:
                    try:
                        print(f"\nFetching page {page_number}...")
                        sessions = get_session_data(page, page_number)
                        
                        # Check if we've reached sessions before 2010
                        if sessions:
                            oldest_date = parse_date(sessions[-1]['date'])
                            if oldest_date and oldest_date.year < cutoff_year:
                                print(f"\nReached sessions from {oldest_date.year}, stopping...")
                                break
                        
                        print(f"\nPage {page_number} summary:")
                        print(f"Found {len(sessions)} sessions")
                        if sessions:
                            print(f"First session: {sessions[0]}")
                            print(f"Last session: {sessions[-1]}")
                        else:
                            print("No sessions found on this page!")
                        
                        writer.writerows(sessions)
                        print(f"Wrote {len(sessions)} sessions to CSV")
                        
                    except Exception as e:
                        print(f"Error on page {page_number}: {e}")
                        print("Retrying after 5 seconds...")
                        time.sleep(5)
                        continue
                    
                    page_number += 1
                    pbar.update(1)
                    time.sleep(2)
        
        browser.close()

if __name__ == "__main__":
    main()
