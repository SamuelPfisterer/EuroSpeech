from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
from dataclasses import dataclass
from typing import List
import re
import csv

@dataclass
class TranscriptLink:
    year: int
    month: str
    day: str
    url: str
    legislation: int
    full_date: datetime = None

    def __post_init__(self):
        # Convert month name to number (handling Latvian month names)
        month_mapping = {
            'Janvāris': 1, 'Februāris': 2, 'Marts': 3, 'Aprīlis': 4,
            'Maijs': 5, 'Jūnijs': 6, 'Jūlijs': 7, 'Augusts': 8,
            'Septembris': 9, 'Oktobris': 10, 'Novembris': 11, 'Decembris': 12
        }
        month_num = month_mapping[self.month]
        
        # Extract the primary day number from potentially complex day strings
        day_match = re.search(r'^\d+', self.day)
        if day_match:
            day = int(day_match.group())
            try:
                self.full_date = datetime(self.year, month_num, day)
            except ValueError:
                # Handle invalid dates
                self.full_date = None

def get_transcript_links(url: str, legislation: int) -> List[TranscriptLink]:
    transcript_links = []
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to URL
        print(f"\nDebug - Processing URL: {url}")
        page.goto(url)
        
        # Get the page content
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all transcript tables
        tables = soup.find_all('table', class_='transcript')
        print(f"Found {len(tables)} transcript tables")
        
        for table in tables:
            # Find the year from the preceding h2 element
            year_element = table.find_previous('h2')
            if not year_element:
                print("Warning: No year element found for table")
                continue
                
            year = int(year_element.text.split('.')[0])
            print(f"Processing year: {year}")
            
            # Process each row in the table
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows in table")
            
            for row in rows:
                # Get month from the first cell
                month_cell = row.find('td', class_='month')
                if not month_cell:
                    continue
                    
                month = month_cell.text.strip()
                print(f"Processing month: {month}")
                
                # Process all links in the row
                links_in_row = row.find_all('a')
                print(f"Found {len(links_in_row)} links in row")
                
                for link in links_in_row:
                    day = link.text.strip()
                    url = f"https://www.saeima.lv{link['href']}"
                    
                    transcript_links.append(TranscriptLink(
                        year=year,
                        month=month,
                        day=day,
                        url=url,
                        legislation=legislation
                    ))
        
        browser.close()
    
    print(f"Total links found: {len(transcript_links)}")
    return transcript_links

def process_legislation(url: str, legislation_number: int) -> List[TranscriptLink]:
    links = get_transcript_links(url, legislation_number)
    sorted_links = sorted(links, key=lambda x: x.full_date if x.full_date else datetime.max)
    print(f"\nLegislation {legislation_number}:")
    print(f"URL: {url}")
    print(f"Total sessions found: {len(links)}")
    print("First session:", sorted_links[0].full_date if sorted_links else "No sessions")
    print("Last session:", sorted_links[-1].full_date if sorted_links else "No sessions")
    print("---")
    return links

def main():
    legislations = {
        7: "https://www.saeima.lv/lv/transcripts/category/26",
        8: "https://www.saeima.lv/lv/transcripts/category/27",
        9: "https://www.saeima.lv/lv/transcripts/category/28",
        10: "https://www.saeima.lv/lv/transcripts/category/15",
        11: "https://www.saeima.lv/lv/transcripts/category/17",
        12: "https://www.saeima.lv/lv/transcripts/category/19",
        13: "https://www.saeima.lv/lv/transcripts/category/21",
        14: "https://www.saeima.lv/lv/transcripts/category/29"
    }
    
    all_links = []
    for legislation_number, url in legislations.items():
        links = process_legislation(url, legislation_number)
        all_links.extend(links)
    
    print(f"\nTotal sessions across all legislations: {len(all_links)}")
    
    # Optional: Add CSV export
    with open('transcript_links.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Year', 'Month', 'Day', 'URL', 'Legislation'])
        for link in all_links:
            writer.writerow([
                link.full_date,
                link.year,
                link.month,
                link.day,
                link.url,
                link.legislation
            ])

if __name__ == "__main__":
    main()
