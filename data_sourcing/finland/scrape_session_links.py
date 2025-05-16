from playwright.sync_api import sync_playwright
import csv
from datetime import datetime
import time

def scrape_session_links():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the main page
        page.goto("https://verkkolahetys.eduskunta.fi/fi/taysistunnot")
        
        # First, load all content by clicking "Load more" until no more content
        print("Loading all sessions...")
        previous_count = 0
        while True:
            current_count = len(page.query_selector_all(".content-card"))
            
            if current_count == previous_count:
                print(f"All sessions loaded. Found {current_count} sessions.")
                break
                
            previous_count = current_count
            
            try:
                load_more = page.get_by_role("button", name="Lataa lisää")
                if not load_more.is_visible():
                    break
                load_more.click()
                time.sleep(2)  # Reduced sleep time since we're just clicking
            except Exception as e:
                print("No more content to load")
                break
        
        # Now get all session data at once
        print("Extracting session data...")
        sessions = []
        cards = page.query_selector_all(".content-card")
        
        for card in cards:
            try:
                # Get title from header
                header = card.query_selector(".header").inner_text()
                
                # Get date
                date_text = card.query_selector(".meta-info span").inner_text()
                
                # Get link
                link_element = card.query_selector("a.overlay-link")
                if link_element:
                    href = link_element.get_attribute("href")
                    full_link = f"https://verkkolahetys.eduskunta.fi{href}"
                    
                    session_data = {
                        "title": header,
                        "date": date_text,
                        "link": full_link
                    }
                    sessions.append(session_data)
            
            except Exception as e:
                print(f"Error processing card: {e}")
                continue
        
        # Save to CSV
        output_file = "session_links.csv"
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "date", "link"])
            writer.writeheader()
            writer.writerows(sessions)
        
        print(f"Successfully scraped {len(sessions)} sessions to {output_file}")
        
        browser.close()

if __name__ == "__main__":
    scrape_session_links() 