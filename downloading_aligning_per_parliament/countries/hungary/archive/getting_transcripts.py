from playwright.sync_api import sync_playwright
import csv
import os
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import time

def read_session_links(csv_file='hungary_parliament_sessions.csv', sample_size=5):
    df = pd.read_csv(csv_file)
    # Get 5 random links using sample() method
    return df['session_link'].sample(n=sample_size).tolist()

def create_output_directories():
    # Create directories if they don't exist
    Path('transcripts/html').mkdir(parents=True, exist_ok=True)
    Path('transcripts/text').mkdir(parents=True, exist_ok=True)

def load_progress():
    try:
        with open('scraping_progress.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'processed_urls': [], 'failed_urls': []}

def save_progress(progress):
    with open('scraping_progress.json', 'w') as f:
        json.dump(progress, f)

def get_transcript_link(page):
    try:
        # Get all matching tables
        tables = page.query_selector_all('table.table.table-bordered')
        
        for table in tables:
            rows = table.query_selector_all('tr')
            
            for row in rows:
                cell = row.query_selector('td')
                if cell and "Ülésnap összes felszólalás szövege" in cell.inner_text().strip():
                    link = row.query_selector('td:nth-child(2) a')
                    if link:
                        return link.get_attribute('href')
        return None
    except Exception as e:
        print(f"Error in get_transcript_link: {e}")
        return None

def extract_text_from_page(page):
    try:
        # Wait for the content to load
        page.wait_for_selector('div[xmlns="http://www.w3.org/1999/xhtml"]')
        
        # Get all text elements using Playwright
        text_elements = page.query_selector_all('div[xmlns="http://www.w3.org/1999/xhtml"] p, div[xmlns="http://www.w3.org/1999/xhtml"] h1, div[xmlns="http://www.w3.org/1999/xhtml"] h2, div[xmlns="http://www.w3.org/1999/xhtml"] h3, div[xmlns="http://www.w3.org/1999/xhtml"] h4, div[xmlns="http://www.w3.org/1999/xhtml"] h5, div[xmlns="http://www.w3.org/1999/xhtml"] h6')
        
        # Extract text from each element
        texts = [element.inner_text().strip() for element in text_elements if element.inner_text().strip()]
        return '\n\n'.join(texts)
    except Exception as e:
        print(f"Error in extract_text_from_page: {e}")
        return ""

def process_sessions():
    # Load all session links
    session_links = read_session_links()
    print(f"\nTotal sessions to process: {len(session_links)}")
    
    # Create directories
    create_output_directories()
    
    # Load progress from previous run
    progress = load_progress()
    
    # Create a list to store mapping information
    transcript_mapping = []
    
    # Read existing mapping if it exists
    if os.path.exists('transcript_mapping.csv'):
        existing_df = pd.read_csv('transcript_mapping.csv')
        transcript_mapping = existing_df.to_dict('records')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set to headless for production
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        # Set default timeout to 30 seconds
        page.set_default_timeout(30000)
        
        start_time = time.time()
        successful_count = 0
        failed_count = 0
        
        try:
            for i, session_url in enumerate(session_links, 1):
                # Skip if already processed successfully
                if session_url in progress['processed_urls']:
                    continue
                
                print(f"\nProcessing session {i} of {len(session_links)} ({i/len(session_links)*100:.1f}%)")
                print(f"URL: {session_url}")
                
                try:
                    # Navigate to session page with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            page.goto(session_url, wait_until='networkidle', timeout=30000)
                            page.wait_for_timeout(3000)
                            break
                        except Exception as e:
                            if attempt == max_retries - 1:
                                raise e
                            print(f"Retry {attempt + 1} after error: {e}")
                            time.sleep(5)
                    
                    # Get transcript link
                    transcript_url = get_transcript_link(page)
                    if not transcript_url:
                        print(f"No transcript link found for session {i}")
                        progress['failed_urls'].append(session_url)
                        failed_count += 1
                        continue
                    
                    # Navigate to transcript page
                    page.goto(transcript_url, wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    # Extract session number and cycle from URL
                    url_parts = transcript_url.split('p_uln%3D')[1].split('%26')
                    session_num = url_parts[0]
                    cycle_num = url_parts[1].split('D')[1].split('%')[0]
                    
                    base_filename = f"cycle_{cycle_num}_session_{session_num}"
                    html_filename = f"transcripts/html/{base_filename}.html"
                    text_filename = f"transcripts/text/{base_filename}.txt"
                    
                    # Save HTML content
                    html_content = page.content()
                    with open(html_filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Extract and save text content
                    text_content = extract_text_from_page(page)
                    with open(text_filename, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    
                    # Add mapping information
                    transcript_mapping.append({
                        'session_url': session_url,
                        'transcript_url': transcript_url,
                        'html_file': html_filename,
                        'text_file': text_filename
                    })
                    
                    # Update progress
                    progress['processed_urls'].append(session_url)
                    successful_count += 1
                    
                    # Save progress every 10 sessions
                    if i % 10 == 0:
                        save_progress(progress)
                        pd.DataFrame(transcript_mapping).to_csv('transcript_mapping.csv', index=False)
                    
                    # Add a small delay between requests
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing session {i}: {e}")
                    progress['failed_urls'].append(session_url)
                    failed_count += 1
                    save_progress(progress)
                
                # Print progress statistics
                elapsed_time = time.time() - start_time
                avg_time_per_session = elapsed_time / i
                remaining_sessions = len(session_links) - i
                estimated_time_remaining = remaining_sessions * avg_time_per_session
                
                print(f"\nProgress Statistics:")
                print(f"Successful: {successful_count}, Failed: {failed_count}")
                print(f"Average time per session: {avg_time_per_session:.1f} seconds")
                print(f"Estimated time remaining: {estimated_time_remaining/3600:.1f} hours")
                
        finally:
            # Save final progress
            save_progress(progress)
            pd.DataFrame(transcript_mapping).to_csv('transcript_mapping.csv', index=False)
            browser.close()
    
    # Final statistics
    print("\nScraping completed!")
    print(f"Total successful: {successful_count}")
    print(f"Total failed: {failed_count}")
    print(f"Total time: {(time.time() - start_time)/3600:.1f} hours")
    
    # Save failed URLs to a separate file
    if progress['failed_urls']:
        pd.DataFrame(progress['failed_urls'], columns=['url']).to_csv('failed_urls.csv', index=False)
        print(f"Failed URLs saved to failed_urls.csv")

if __name__ == "__main__":
    process_sessions() 