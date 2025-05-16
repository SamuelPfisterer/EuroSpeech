from playwright.sync_api import sync_playwright
import pandas as pd
from typing import List, Dict
import re 
import datetime as datetime
from tqdm import tqdm

def extract_date(text: str) -> str:
    """Extract date from German format (e.g., '16. Oktober 2024')."""
    try:
        # German month names mapping
        MONTH_MAP = {
            'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04',
            'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
            'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'
        }
        
        # Regular expression to match German date format
        pattern = r'(\d{1,2})\.\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(\d{4})'
        match = re.search(pattern, text)
        
        if match:
            day = match.group(1).zfill(2)  # Pad single digit days with leading zero
            month = MONTH_MAP[match.group(2)]
            year = match.group(3)
            return f"{year}-{month}-{day}"
        
        return None
    except Exception:
        return None

def extract_title_and_date(page):
    page.wait_for_selector("h3.bt-artikel__title", 
                          state="visible", 
                          timeout=5000)
    title_elements = page.locator("h3.bt-artikel__title, h3.bt-artikel__title span.bt-dachzeile").all_text_contents()
    title = ' '.join([text.strip() for text in title_elements if text.strip()])
    
    date = extract_date(title) if title else None
    return title, date

def get_mp4_links_from_iframe(page):
    frame = page.frame_locator('iframe[src*="webtv.bundestag.de/statics/tplayer"]:not([title*="Livestream"])')
    
    try:
        page.wait_for_selector('iframe[src*="webtv.bundestag.de/statics/tplayer"]:not([title*="Livestream"])', 
                              timeout=5000)

        
        elements = frame.locator("div[data-value*='mp4']").all()
        mp4_links = []
        for element in elements:
            data_value = element.get_attribute("data-value")
            if data_value:
                mp4_links.append(data_value)
        return mp4_links
    except Exception as e:
        print(f"Error in iframe: {str(e)}")
        return None

def get_srt_link(page):
    frame = page.frame_locator('iframe[src*="webtv.bundestag.de/statics/tplayer"]:not([title*="Livestream"])')
    
    try:
        page.wait_for_selector('iframe[src*="webtv.bundestag.de/statics/tplayer"]:not([title*="Livestream"])', 
                              timeout=5000)
        
        elements = frame.locator("div[data-value*='.srt']").all()
        srt_links = []
        for element in elements:
            data_value = element.get_attribute("data-value")
            if data_value:
                srt_links.append(data_value)
        return srt_links[0] if srt_links else None
    except Exception as e:
        print(f"Error in iframe: {str(e)}")
        return None

def scrape_bundestag_videos(video_links: List[str]) -> tuple[pd.DataFrame, List[str]]:
    video_data = []
    error_links = []  # Store links that had errors

    consecutive_no_srt = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        with tqdm(total=len(video_links), desc="Processing videos") as pbar:
        
            for i, link in enumerate(video_links):
                try:
                    page.goto(link, wait_until="domcontentloaded")
                    
                    title, date = extract_title_and_date(page)
                    mp4_links = get_mp4_links_from_iframe(page)
                    srt_link = get_srt_link(page)
                    
                    # Get the 514.mp4 link if available
                    mp4_514_link = next((link[:link.find('.mp4') + 4] 
                                    for link in mp4_links 
                                    if '514.mp4' in link), None) if mp4_links else None
                    
                    # Check for SRT file
                    
                    video_data.append({
                        'link': link,
                        'title': title,
                        'date': date,
                        'mp4_links': mp4_links,
                        '514_mp4_truncated': mp4_514_link,
                        'srt_link': srt_link
                    })
                    
                    # Stop if we've found 20 consecutive videos without SRT
                    if consecutive_no_srt >= 20:
                        print("Stopping: Found 20 consecutive videos without SRT files")
                        print(f"Processed {i+1} videos")
                        print(f"Last video processed: {link}")
                        break
                    
                except Exception as e:
                    error_message = f"Error processing {link}: {str(e)}"
                    pbar.write(error_message)
                    error_links.append(link)
                    continue
                
                finally:
                    pbar.update(1)
        
        browser.close()
    
    return pd.DataFrame(video_data), error_links

if __name__ == "__main__":
    # Assuming video_links is your list of links to process
    video_links = pd.read_csv("aussschuss_links.csv")['full_link'].tolist()
    
    df, error_links = scrape_bundestag_videos(video_links)

    print(f"\nProcessing completed:")
    print(f"Successfully processed: {len(df)} videos")
    print(f"Failed to process: {len(error_links)} videos")

    # Save results
    df.to_csv('germany_auschuss_file_links.csv', index=False)

    if error_links:
        # Save error links to a file
        with open('germany_auschuss_error_links.txt', 'w') as f:
            for link in error_links:
                f.write(f"{link}\n")