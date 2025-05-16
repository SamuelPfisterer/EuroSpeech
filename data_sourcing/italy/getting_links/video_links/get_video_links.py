from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import csv
import os
import random

def setup_stealth_browser(playwright):
    """Configure browser with stealth settings"""
    return playwright.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized'
        ]
    )

def setup_stealth_context(browser):
    """Configure browser context with stealth settings"""
    return browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        java_script_enabled=True,
        ignore_https_errors=True,
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
    )

def random_delay():
    """Add random delay between requests"""
    time.sleep(random.uniform(2, 4))

def extract_session_info(page):
    sessions = []
    
    # Get all cards
    cards = page.query_selector_all(".sw-card.sw-card--sp-vertical.views-row")
    print(f"Found {len(cards)} cards")
    
    for card in cards:
        try:
            # Extract label
            label = card.query_selector(".label.secondary")
            label_text = label.inner_text().strip() if label else ""
            
            # Extract date
            date_elem = card.query_selector("time")
            date_text = date_elem.get_attribute("datetime") if date_elem else ""
            
            # Extract title and session number
            title_elem = card.query_selector(".sw-list-item__content__title h3 a")
            title = title_elem.inner_text().strip() if title_elem else ""
            session_number = ""
            if title:
                import re
                match = re.search(r'no\.\s*(\d+)', title)
                if match:
                    session_number = match.group(1)
            
            # Extract detail link
            detail_link = title_elem.get_attribute("href") if title_elem else ""
            if detail_link and not detail_link.startswith("http"):
                detail_link = f"https://webtv.senato.it{detail_link}"
            
            session_info = [
                label_text,
                date_text,
                title,
                session_number,
                detail_link
            ]
            sessions.append(session_info)
            
        except Exception as e:
            print(f"Error extracting session info: {str(e)}")
            continue
    
    return sessions

def main():
    output_file = "senate_sessions.csv"
    headers = ["label", "date", "title", "session_number", "detail_link"]
    total_sessions = 0
    
    # Create CSV file and write headers
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    
    with sync_playwright() as p:
        browser = setup_stealth_browser(p)
        context = setup_stealth_context(browser)
        page = context.new_page()
        
        # Loop through all pages (0 to 456)
        for page_num in range(457):
            try:
                url = f"https://webtv.senato.it/webtv/assemblea?sort_by=field_date&sort_order=DESC&page={page_num}"
                print(f"\nProcessing page {page_num}")
                
                # Navigate to the page with random delay
                page.goto(url)
                random_delay()
                
                # Wait for content to load
                page.wait_for_selector(".sw-card", timeout=15000)
                
                # Extract session information
                sessions = extract_session_info(page)
                total_sessions += len(sessions)
                print(f"Found {len(sessions)} sessions on page {page_num}")
                
                # Append new sessions to CSV
                with open(output_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(sessions)
                
                # Progress update
                print(f"Total sessions so far: {total_sessions}")
                
            except Exception as e:
                print(f"Error processing page {page_num}: {str(e)}")
                # Save progress so far and continue
                continue
            
            # Random delay between pages
            random_delay()
        
        browser.close()
    
    print(f"\nScraping completed.")
    print(f"Total sessions found: {total_sessions}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
