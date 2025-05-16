from playwright.sync_api import sync_playwright
import random
import time
import csv
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SessionScraper:
    def __init__(self):
        self.sessions = []
        self.base_url = "https://www.riksdagen.se/sv/sok/?avd=webbtv&doktyp=bet&p="
        
    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add random delay to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def init_browser(self, playwright):
        """Initialize browser with stealth settings"""
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Add human-like behaviors
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return browser, context
        
    def parse_duration(self, duration_str):
        """Parse ISO 8601 duration string into a readable format"""
        if not duration_str or not duration_str.startswith('PT'):
            return None
            
        duration = duration_str[2:]  # Remove 'PT' prefix
        hours = '0'
        minutes = '0'
        seconds = '0'
        
        if 'H' in duration:
            hours, duration = duration.split('H')
        if 'M' in duration:
            minutes, duration = duration.split('M')
        if 'S' in duration:
            seconds = duration.replace('S', '')
            
        return f"{hours.zfill(2)}:{minutes.zfill(2)}:{seconds.zfill(2)}"
        
    def extract_session_info(self, session_element):
        """Extract information from a session element"""
        try:
            # Extract title
            title_element = session_element.query_selector('h3 a')
            title = title_element.inner_text() if title_element else "No title"
            
            # Extract link
            link = title_element.get_attribute('href') if title_element else None
            # Fix link format - only add base URL if it's not already there
            if link:
                if link.startswith('/'):
                    link = f"https://www.riksdagen.se{link}"
                elif not link.startswith('http'):
                    link = f"https://www.riksdagen.se/{link}"
            
            # Extract date - look specifically for the date in the paragraph element
            date_element = session_element.query_selector('p.sc-9f03358b-1 time')
            if date_element:
                date_str = date_element.get_attribute('datetime')
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d') if date_str else None
                except ValueError:
                    logging.warning(f"Could not parse date string: {date_str}")
                    date = None
            else:
                date = None
                
            # Extract duration
            duration_element = session_element.query_selector('span.dLGIzr time')
            duration_str = duration_element.get_attribute('datetime') if duration_element else None
            duration = self.parse_duration(duration_str)
            
            session_info = {
                'title': title,
                'link': link,
                'date': date,
                'duration': duration
            }
            
            # Only return if we have at least a title and link
            if session_info['title'] and session_info['link']:
                return session_info
            return None
            
        except Exception as e:
            logging.error(f"Error extracting session info: {e}")
            return None
            
    def scrape_sessions(self):
        """Main scraping function"""
        with sync_playwright() as playwright:
            browser, context = self.init_browser(playwright)
            page = context.new_page()
            
            page_num = 1
            has_next_page = True
            
            try:
                while has_next_page:
                    url = f"{self.base_url}{page_num}"
                    logging.info(f"Scraping page {page_num}")
                    
                    # Navigate to page with random delay
                    self.random_delay()
                    page.goto(url)
                    
                    # Wait for content to load
                    page.wait_for_selector('ul li div.sc-9f03358b-0', timeout=10000)
                    
                    # Extract sessions from current page
                    sessions = page.query_selector_all('ul li div.sc-9f03358b-0')
                    
                    # Check if we've reached the last page (no sessions found)
                    if not sessions:
                        logging.info("No more sessions found. Reached the last page.")
                        break
                        
                    # Process each session
                    sessions_found = 0
                    for session in sessions:
                        session_info = self.extract_session_info(session)
                        if session_info:
                            self.sessions.append(session_info)
                            sessions_found += 1
                            logging.info(f"Found session: {session_info['title']} ({session_info['date']}) - Duration: {session_info['duration']}")
                    
                    logging.info(f"Found {sessions_found} sessions on page {page_num}")
                            
                    # Random delay before next page
                    self.random_delay()
                    page_num += 1
                    
            except Exception as e:
                logging.error(f"Error during scraping: {e}")
            finally:
                browser.close()
                
    def save_to_file(self, filename='sessions.csv'):
        """Save scraped sessions to CSV file"""
        try:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'date', 'duration', 'link'])
                writer.writeheader()
                writer.writerows(self.sessions)
            logging.info(f"Saved {len(self.sessions)} sessions to {filename}")
        except Exception as e:
            logging.error(f"Error saving to file: {e}")

def main():
    scraper = SessionScraper()  # No page limit
    scraper.scrape_sessions()
    scraper.save_to_file()

if __name__ == "__main__":
    main()
