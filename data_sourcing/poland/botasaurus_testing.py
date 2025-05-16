from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
from botasaurus.browser import Wait
import csv
import time

def generate_links():
    return [f"https://www.senat.gov.pl/prace/posiedzenia/?k={legislation}&pp=100" 
            for legislation in range(8, 12)]

@browser(
    reuse_driver=True,
    headless=False,
    data=generate_links()
)
def scrape_heading_task(driver: Driver, url):
    # Extract legislation number from URL
    legislation = url.split('k=')[1].split('&')[0]
    print(f"\nProcessing legislation {legislation}")
    
    # Visit the website via Google Referrer
    driver.google_get(url)
    
    # Instead of prompt, use sleep
    time.sleep(5)  # Wait 5 seconds
    container = driver.select(".modul-kontener", wait=Wait.VERY_LONG)
    
    # Get the page source as BeautifulSoup object
    soup = soupify(driver)
    
    results = []
    meetings = soup.find_all('div', class_="meeting container-posiedzenia")
    
    for meeting in meetings:
        # Extracting data from the meeting div
        session_title = meeting.find('h3', class_='meeting-headline').get_text(strip=True)
        session_number = session_title.split('.')[0]
        session_date = meeting.find('div', class_='date-container').find('span').get_text(strip=True)
        
        link_to_session = meeting.find('h3', class_='meeting-headline').find('a')['href']
        link_to_session = f"https://www.senat.gov.pl{link_to_session}"
        
        pdf_link = None
        video_link = None
        transcript_links = []
        
        # Finding PDF and other links
        details = meeting.find_all('div', class_='details')
        for detail in details:
            anchor = detail.find('a')
            
            if anchor:
                link_text = anchor.get_text(strip=True)
                href = f"https://www.senat.gov.pl{anchor['href']}"
                if 'PDF' in link_text:
                    pdf_link = href
                elif 'video' in link_text.lower():
                    video_link = href
        
        # Extracting all transcript links
        transcript_links = []
        print(f"Processing session {session_number}")
        
        # First find the menu container for transcripts
        menu_container = meeting.find('ul', class_='menu-zakladki-posiedzenia')
        
        if menu_container:
            # Find li that contains Stenogram
            stenogram_li = menu_container.find('li', recursive=False)  # Only direct children
            if stenogram_li:
                # Verify this is the Stenogram section by checking the label
                label_span = stenogram_li.find('span', class_='label', string='Stenogram')
                if label_span:
                    # First check for submenu (multiple days)
                    day_menu = stenogram_li.find('ul', class_='menu-zakladki-posiedzenia-poziom2')
                    if day_menu:
                        # Multiple days case
                        day_links = day_menu.find_all('a')
                        for day_link in day_links:
                            full_link = f"https://www.senat.gov.pl{day_link['href']}"
                            transcript_links.append(full_link)
                    else:
                        # Single day case - use the main Stenogram link
                        stenogram_link = stenogram_li.find('a', class_='middle-element')['href']
                        full_link = f"https://www.senat.gov.pl{stenogram_link}"
                        transcript_links.append(full_link)
        
        if transcript_links:
            print(f"Found {len(transcript_links)} transcript link(s)")

        results.append({
            "legislation": legislation,
            "session_title": session_title,
            "session_number": session_number,
            "session_date": session_date,
            "link_to_session": link_to_session,
            "pdf_link": pdf_link,
            "transcript_links": ','.join(transcript_links),  # Join multiple links with comma
            "video_link": video_link
        })
    
    return results

def save_results(all_results):
    # Save all results to CSV
    csv_file = 'poland_senate_sessions.csv'
    fieldnames = ["legislation", "session_title", "session_number", "session_date", "link_to_session", 
                 "pdf_link", "transcript_links", "video_link"]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"Results saved to '{csv_file}'")

if __name__ == "__main__":
    # Get results for all legislations
    all_results = scrape_heading_task()
    # Flatten the list of results
    flattened_results = [item for sublist in all_results for item in sublist]
    # Save all results to CSV
    save_results(flattened_results)
