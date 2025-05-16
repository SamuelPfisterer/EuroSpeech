from playwright.sync_api import sync_playwright
import csv
import re
from datetime import datetime

def read_cycle_links(filename='cycle_links.txt'):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def extract_session_info(page, url):
    # Navigate to the page
    page.goto(url)
    
    # Wait for the table to load
    page.wait_for_selector('.table.table-bordered')
    
    sessions = []
    
    # Get all rows from tbody
    rows = page.query_selector_all('tbody tr')
    
    for row in rows:
        # Get date column (first td)
        date_cell = row.query_selector('td:first-child a')
        if not date_cell:
            continue
            
        date_text = date_cell.inner_text()
        
        # Extract date and session number using regex
        match = re.match(r'(\d{4}\.\d{2}\.\d{2}\.)\((\d+)\)', date_text)
        if match:
            date_str, session_number = match.groups()
            # Convert date from "YYYY.MM.DD." format to "YYYY-MM-DD"
            date = datetime.strptime(date_str, '%Y.%m.%d.').strftime('%Y-%m-%d')
        else:
            continue
            
        # Get session link
        session_link = date_cell.get_attribute('href')
        
        # Get video link from third column
        video_cell = row.query_selector('td:nth-child(3) a')
        video_link = video_cell.get_attribute('href') if video_cell else ''
        
        # Get nature of sitting from fifth column
        nature_cell = row.query_selector('td:nth-child(5)')
        nature_of_sitting = nature_cell.inner_text().strip() if nature_cell else ''
        
        # Get day from sixth column
        day_cell = row.query_selector('td:nth-child(6)')
        day = day_cell.inner_text().strip() if day_cell else ''
        
        session_info = {
            'date': date,
            'session_number': session_number,
            'session_link': session_link,
            'video_link': video_link,
            'nature_of_sitting': nature_of_sitting,
            'day': day
        }
        
        sessions.append(session_info)
    
    return sessions

def save_to_csv(sessions, filename='hungary_parliament_sessions.csv'):
    fieldnames = ['date', 'session_number', 'session_link', 'video_link', 'nature_of_sitting', 'day']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sessions)

def main():
    # Read cycle links from file
    cycle_links = read_cycle_links()
    all_sessions = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            for i, url in enumerate(cycle_links, 1):
                print(f"Processing cycle {i} of {len(cycle_links)}...")
                sessions = extract_session_info(page, url)
                all_sessions.extend(sessions)
                print(f"Found {len(sessions)} sessions in cycle {i}")
            
            save_to_csv(all_sessions)
            print(f"Successfully scraped {len(all_sessions)} sessions total")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
