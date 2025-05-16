from playwright.sync_api import sync_playwright
from typing import Set
import pandas as pd

def scrape_bundestag_videos():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Navigating to Bundestag media page...")
        page.goto("https://www.bundestag.de/mediathek/ausschusssitzungen")
        
        video_links: Set[str] = set()
        current_page = 0
        
        try:
            while True and current_page < 1000:
                # On every second page, wait for videos to be visible
                if current_page % 2 == 0:
                    print(f"Page {current_page}: Waiting for videos to load...")
                    # Wait for video elements to be visible
                    page.locator(".bt-open-in-overlay").first.wait_for(
                        state="visible", 
                        timeout=10000
                    )
                
                # Collect links
                links = page.query_selector_all(".bt-open-in-overlay")
                current_links = {link.get_attribute('href') for link in links}
                previous_count = len(video_links)
                video_links.update(current_links)
                
                new_links = len(video_links) - previous_count
                print(f"Page {current_page}: Found {new_links} new videos (Total: {len(video_links)})")
                
                try:
                    next_button = page.locator(".slick-next").first
                    next_button.wait_for(state="visible", timeout=10000)
                    
                    if not next_button.is_visible():
                        break
                        
                    next_button.click()
                    current_page += 1
                    
                except Exception:
                    print("Reached last page")
                    break
                    
        finally:
            browser.close()
            
        return list(video_links)

if __name__ == "__main__":
    links = scrape_bundestag_videos()
    print(f"\nTotal unique videos: {len(links)}")
    print("\nFirst 5 links:")
    df = pd.DataFrame(links)
    df.to_csv("aussschuss_links.csv", index=False)
    for link in list(links)[:5]:
        print(f"- {link}")