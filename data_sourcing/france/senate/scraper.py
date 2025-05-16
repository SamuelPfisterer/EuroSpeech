import csv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin
import logging
import time
from camoufox.sync_api import Camoufox
import subprocess
import re


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://videos.senat.fr/"
START_URL_TEMPLATE = "https://videos.senat.fr/chaine.seance-publique.p{}"
TOTAL_PAGES = 444 # Adjust if necessary, e.g., set to 2 for testing, all pages = 444
OUTPUT_CSV = "senate_videos.csv"
RETRY_DELAY = 5 # seconds between retries
MAX_RETRIES = 3

def get_page_with_retries(page, url, retries=MAX_RETRIES):
    """Attempts to navigate to a URL with retries."""
    for attempt in range(retries):
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            logging.info(f"Successfully loaded {url}")
            return True
        except PlaywrightTimeoutError:
            logging.warning(f"Timeout loading {url} on attempt {attempt + 1}/{retries}. Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logging.error(f"Failed to load {url} on attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"Max retries reached for {url}. Giving up.")
                return False
    return False

def get_m3u8_duration(m3u8_url):
    """Get duration of M3U8 stream using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            m3u8_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            duration_seconds = float(result.stdout.strip())
            return duration_seconds
    except Exception as e:
        logging.warning(f"Could not get duration for {m3u8_url}: {str(e)}")
    return None

def main():
    with Camoufox(
        headless=False
    ) as browser:
        page = browser.new_page()
        # Optional: Add headers to mimic a real browser
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        processed_urls = set() # Keep track of processed session URLs to avoid duplicates

        try:
            with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'session_url' in row and row['session_url'] not in ('Error Processing', ''):
                         processed_urls.add(row['session_url'])
                logging.info(f"Loaded {len(processed_urls)} previously processed URLs from {OUTPUT_CSV}")
        except FileNotFoundError:
            logging.info(f"{OUTPUT_CSV} not found. Starting fresh.")
            # Create header if file doesn't exist
            with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
                 fieldnames = ['session_url', 'm3u8_url', 'vtt_url', 'duration']
                 writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                 writer.writeheader()


        with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['session_url', 'm3u8_url', 'vtt_url', 'duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            logging.info(f"Starting scrape for {TOTAL_PAGES} pages. Outputting to {OUTPUT_CSV}")

            for page_num in range(1, TOTAL_PAGES + 1):
                list_page_url = START_URL_TEMPLATE.format(page_num)
                logging.info(f"Processing list page {page_num}/{TOTAL_PAGES}: {list_page_url}")

                if not get_page_with_retries(page, list_page_url):
                    logging.error(f"Skipping page {page_num} due to loading errors.")
                    continue # Skip to next list page

                # Find all session card elements
                session_cards = []
                try:
                     # Wait briefly for cards to potentially load via JS
                     page.wait_for_selector('div.swiper-slide div.card a.stretched-link', timeout=10000)
                     session_cards = page.locator('div.swiper-slide div.card a.stretched-link').all()
                except PlaywrightTimeoutError:
                     logging.warning(f"Timeout waiting for session cards on page {page_num}. Might be empty or slow loading.")
                except Exception as e:
                     logging.error(f"Error finding session card locators on page {page_num}: {e}")


                if not session_cards:
                    logging.warning(f"No session cards found on page {page_num}.")
                    continue

                session_links_on_page = []
                for card_link in session_cards:
                    try:
                        relative_link = card_link.get_attribute('href')
                        if relative_link and relative_link.startswith('video.'):  # Only process video links
                             full_session_url = urljoin(BASE_URL, relative_link.strip())
                             # Remove timecode parameter if present for cleaner URL comparison
                             full_session_url = urljoin(full_session_url, urlparse(full_session_url).path)
                             session_links_on_page.append(full_session_url)
                        else:
                             logging.warning(f"Skipping non-video link: {relative_link}")
                    except Exception as e:
                        logging.error(f"Error extracting link from card on page {page_num}: {e}")


                logging.info(f"Found {len(session_links_on_page)} potential session links on page {page_num}.")

                for session_url in session_links_on_page:
                    if session_url in processed_urls:
                        logging.info(f"Skipping already processed session: {session_url}")
                        continue

                    logging.info(f"Processing session: {session_url}")
                    m3u8_url = 'Not Found'
                    vtt_url = 'Not Found'
                    row_data = {'session_url': session_url, 'm3u8_url': m3u8_url, 'vtt_url': vtt_url} # Default

                    try:
                        if not get_page_with_retries(page, session_url):
                             logging.error(f"Skipping session {session_url} due to loading errors.")
                             row_data['m3u8_url'] = 'Error Loading Page'
                             row_data['vtt_url'] = 'Error Loading Page'
                             writer.writerow(row_data)
                             processed_urls.add(session_url) # Mark as processed even if failed
                             continue


                        # Wait for the player container to be present
                        player_container_locator = page.locator('div.html5player_container')
                        try:
                            player_container_locator.wait_for(state='visible', timeout=20000)
                        except PlaywrightTimeoutError:
                            logging.warning(f"Player container did not become visible for {session_url}")
                            # Continue anyway, maybe tags are present but hidden

                        # --- Get M3U8 from <source> tag ---
                        try:
                             source_tag = player_container_locator.locator('video source')
                             # Ensure the element exists before getting attribute
                             if source_tag.count() > 0:
                                 m3u8_src = source_tag.first.get_attribute('src')
                                 if m3u8_src and m3u8_src.strip():
                                     m3u8_url = m3u8_src.strip()
                                     logging.info(f"Found m3u8 via <source>: {m3u8_url}")
                                     row_data['m3u8_url'] = m3u8_url
                                     
                                     # Get duration
                                     duration = get_m3u8_duration(m3u8_url)
                                     if duration:
                                         hours = int(duration // 3600)
                                         minutes = int((duration % 3600) // 60)
                                         seconds = int(duration % 60)
                                         row_data['duration'] = f"{hours}h {minutes}m {seconds}s"
                                     else:
                                         row_data['duration'] = 'Unknown'
                                 else:
                                      logging.warning(f"Found <source> tag but src is empty for {session_url}")

                             else:
                                logging.warning(f"Could not find <source> tag within player for {session_url}")
                        except Exception as e:
                             logging.warning(f"Error finding/parsing m3u8 <source> tag for {session_url}: {e}")

                        # --- Get VTT from <track> tag ---
                        try:
                            # Attempt to find the French track first
                            track_tag = player_container_locator.locator('video track[srclang="fr"]')
                            if track_tag.count() == 0:
                                # Fallback to any track if French isn't found
                                track_tag = player_container_locator.locator('video track')

                            if track_tag.count() > 0:
                                relative_vtt_src = track_tag.first.get_attribute('src')
                                if relative_vtt_src and relative_vtt_src.strip():
                                    vtt_url_full = urljoin(BASE_URL, relative_vtt_src.strip())
                                    logging.info(f"Found vtt: {vtt_url_full}")
                                    row_data['vtt_url'] = vtt_url_full
                                else:
                                    logging.warning(f"Found <track> tag but src attribute is empty for {session_url}")
                            else:
                                logging.warning(f"Could not find any vtt <track> tag for {session_url}")
                        except Exception as e:
                            logging.warning(f"Error finding/parsing vtt <track> tag for {session_url}: {e}")


                    except Exception as e:
                        logging.error(f"General failure processing session {session_url}: {e}")
                        row_data['m3u8_url'] = 'Error Processing Session'
                        row_data['vtt_url'] = 'Error Processing Session'

                    # Write data row
                    writer.writerow(row_data)
                    csvfile.flush() # Ensure data is written immediately
                    processed_urls.add(session_url) # Mark as processed

        logging.info(f"Scraping finished. Data saved to {OUTPUT_CSV}")
        browser.close()

if __name__ == "__main__":
    # Need to import urlparse for cleaning URLs
    from urllib.parse import urlparse
    main() 