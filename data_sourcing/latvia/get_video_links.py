from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
from dataclasses import dataclass
from typing import List
import re
import csv

@dataclass
class VideoLink:
    date: datetime
    time: str
    url: str
    legislation: int
    title: str = None  # For special cases like "Robertas Metsolas uzruna"

def parse_latvian_date(date_str: str) -> datetime:
    """Convert date from DD.MM.YYYY. format to datetime object"""
    try:
        return datetime.strptime(date_str.strip('.'), '%d.%m.%Y')
    except ValueError:
        return None

def get_video_links(url: str, legislation: int) -> List[VideoLink]:
    video_links = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"\nDebug - Processing URL: {url}")
        page.goto(url)
        
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        for table in tables:
            rows = table.find_all('tr')
            print(f"Processing table with {len(rows)} rows")
            
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Get date from first cell
                date_cell = cells[0].text.strip()
                date = parse_latvian_date(date_cell)
                if not date:
                    continue
                
                # Process each cell in the row that might contain links
                for cell in cells[1:]:
                    link = cell.find('a')
                    if not link:
                        continue
                        
                    url = link.get('href')
                    if not url:
                        continue
                        
                    # Ensure URL is properly formatted
                    if not url.startswith('http'):
                        if url.startswith('/'):
                            url = f"https://www.saeima.lv{url}"
                        else:
                            url = f"https://{url.strip()}"
                    
                    # Clean up URL (remove any admin prefixes)
                    if '/admin/pages/edit/' in url:
                        url = url.split('/admin/pages/edit/')[-1]
                    
                    time_text = link.text.strip()
                    title = None
                    
                    # Check if it's a special case (like a speech) or regular time
                    if not re.match(r'^\d{1,2}[:.]\d{2}$', time_text):
                        title = time_text
                        time_text = None
                    
                    video_links.append(VideoLink(
                        date=date,
                        time=time_text,
                        url=url,
                        legislation=legislation,
                        title=title
                    ))
        
        browser.close()
    
    return video_links

def process_legislation(url: str, legislation_number: int) -> List[VideoLink]:
    links = get_video_links(url, legislation_number)
    sorted_links = sorted(links, key=lambda x: (x.date, x.time or ""))
    
    print(f"\nLegislation {legislation_number}:")
    print(f"URL: {url}")
    print(f"Total videos found: {len(links)}")
    print("First video:", sorted_links[0].date if sorted_links else "No videos")
    print("Last video:", sorted_links[-1].date if sorted_links else "No videos")
    print("---")
    
    return links

def main():
    legislations = {
        11: "https://www.saeima.lv/lv/likumdosana/saeimas-sede/video-translacijas/11-saeimas-sezu-videotranslacijas",
        12: "https://www.saeima.lv/lv/likumdosana/saeimas-sedes/videotranslacijas/12-saeimas-videotranslacijas/",
        13: "https://www.saeima.lv/lv/likumdosana/saeimas-sedes/videotranslacijas/13-saeimas-sezu-videotranslacijas/",
        14: "https://www.saeima.lv/lv/likumdosana/saeimas-sedes/videotranslacijas/14-saeimas-sezu-videotranslacijas/"
    }
    
    all_links = []
    for legislation_number, url in legislations.items():
        links = process_legislation(url, legislation_number)
        all_links.extend(links)
    
    # Also process the 2024 page for 14th legislation
    links_2024 = process_legislation(
        "https://www.saeima.lv/lv/likumdosana/saeimas-sede/videotranslacijas",
        14
    )
    all_links.extend(links_2024)
    
    print(f"\nTotal videos across all legislations: {len(all_links)}")
    
    # Export to CSV
    with open('video_links.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Time', 'URL', 'Legislation', 'Title'])
        for link in all_links:
            writer.writerow([
                link.date,
                link.time,
                link.url,
                link.legislation,
                link.title
            ])

if __name__ == "__main__":
    main() 