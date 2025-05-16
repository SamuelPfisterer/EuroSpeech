from playwright.sync_api import sync_playwright
import pandas as pd
import time
import json
from pathlib import Path

def setup_stealth_browser():
    """Initialize playwright browser with stealth mode"""
    playwright = sync_playwright().start()
    
    # Use chromium with stealth mode
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Add stealth mode scripts
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return playwright, browser, context

def extract_speech_data(page):
    """Extract speech segments and timing data from the page"""
    
    # Get timing data from speakers list
    speakers_data = []  # New list to store raw speakers data
    timing_data = {}
    
    print("\nDebug: Starting speakers list extraction...")
    
    # Look for speakers list by ID
    print("Debug: Looking for speakers list by ID...")
    speakers_list = page.query_selector('#speakers-list')
    print(f"Debug: Found speakers-list? {speakers_list is not None}")
    
    if speakers_list:
        print("\nDebug: Found speakers list, examining structure...")
        print(f"HTML of speakers-list: {speakers_list.inner_html()[:500]}...")
        
        # Get all list items
        list_items = speakers_list.query_selector_all('li')
        print(f"\nDebug: Found {len(list_items)} speaker list items")
        
        for idx, item in enumerate(list_items):
            try:
                print(f"\nProcessing item {idx + 1}")
                link = item.query_selector('a')
                if not link:
                    print(f"No link found in item {idx + 1}")
                    continue
                
                href = link.get_attribute('href')
                time_element = link.query_selector('time')
                speaker_element = link.query_selector('.sc-31b8789-2')
                
                print(f"Item {idx + 1} data:")
                print(f"- href: {href}")
                print(f"- time: {time_element.inner_text() if time_element else None}")
                print(f"- speaker: {speaker_element.inner_text() if speaker_element else None}")
                
                if href and time_element and speaker_element:
                    pos = href.split('pos=')[1].split('&')[0]
                    timestamp = time_element.inner_text()
                    
                    # Convert timestamp to seconds
                    if timestamp:
                        parts = timestamp.split(':')
                        if len(parts) == 2:
                            minutes, seconds = map(int, parts)
                            total_seconds = minutes * 60 + seconds
                        else:
                            total_seconds = None
                    else:
                        total_seconds = None
                    
                    # Store in timing_data for matching with speeches
                    timing_data[pos] = {
                        'timestamp': timestamp,
                        'position_seconds': total_seconds,
                        'speaker': speaker_element.inner_text()
                    }
                    
                    # Store raw speaker data
                    speakers_data.append({
                        'speaker': speaker_element.inner_text(),
                        'timestamp': timestamp,
                        'position_seconds': total_seconds,
                        'video_position': pos,
                        'href': href
                    })
                    print(f"Successfully processed speaker: {speaker_element.inner_text()}")
            except Exception as e:
                print(f"Error processing item {idx + 1}: {e}")
                continue
    else:
        print("\nDebug: Could not find #speakers-list")
        print("Looking for any elements with 'speaker' in their ID...")
        elements = page.query_selector_all('[id*="speaker"]')
        for elem in elements:
            print(f"Found element with ID: {elem.get_attribute('id')}")
            print(f"Class: {elem.get_attribute('class')}")
            print(f"HTML: {elem.inner_html()[:200]}...")
    
    print(f"\nDebug: Total speakers data collected: {len(speakers_data)}")
    
    # Get speech segments
    speeches = []
    content_div = page.query_selector('#Accordion-video-protocol-0-content')
    if not content_div:
        print("Could not find transcript content div")
        return []
        
    for speech_div in content_div.query_selector_all('.sc-5be275a0-1'):
        try:
            # Extract speaker info
            speaker_link = speech_div.query_selector('.sc-d9f50bcf-0')
            speaker_name = speaker_link.inner_text().strip() if speaker_link else None
            
            # Extract speech number and title
            title = speech_div.query_selector('h3')
            speech_num = title.inner_text() if title else None
            
            # Extract content
            content_div = speech_div.query_selector('.sc-7f1468f0-0')
            content = content_div.inner_text() if content_div else None
            
            # Extract video position link
            pos_link = speech_div.query_selector('.sc-51573eba-1 a')
            if pos_link:
                href = pos_link.get_attribute('href')
                pos = href.split('pos=')[1] if 'pos=' in href else None
                
                # Match with timing data
                timing = timing_data.get(pos, {})
                timestamp = timing.get('timestamp')
                position_seconds = timing.get('position_seconds')
            else:
                pos = None
                timestamp = None
                position_seconds = None

            speeches.append({
                'speaker': speaker_name,
                'speech_number': speech_num,
                'content': content,
                'video_position': pos,  # Original position parameter
                'timestamp': timestamp,  # HH:MM format
                'position_seconds': position_seconds,  # Position in seconds
            })
            
        except Exception as e:
            print(f"Error extracting speech: {e}")
            continue
            
    return speeches, speakers_data

def get_transcript(url, output_dir='transcripts'):
    """Get transcript for a single session URL"""
    
    playwright, browser, context = setup_stealth_browser()
    
    try:
        page = context.new_page()
        page.goto(url)
        
        # Wait for and click the button that reveals the transcript
        print("Waiting for transcript button...")
        button_selector = '#Accordion-video-protocol-0-button'
        page.wait_for_selector(button_selector, timeout=10000)
        
        # Get button state
        button = page.query_selector(button_selector)
        is_expanded = button.get_attribute('aria-expanded') == 'true'
        print(f"Button found. Current aria-expanded state: {is_expanded}")
        
        # Only click if not already expanded
        if not is_expanded:
            print("Clicking button to expand transcript...")
            page.click(button_selector)
        else:
            print("Transcript already expanded")
        
        # Now wait for the content to be visible
        print("Waiting for transcript content to be visible...")
        page.wait_for_selector('#Accordion-video-protocol-0-content', state='visible', timeout=10000)
        time.sleep(2)  # Additional wait to ensure dynamic content loads
        
        print("Starting to extract speech data...")
        speeches, speakers_data = extract_speech_data(page)
        
        # Save both speeches and speakers data
        if speeches or speakers_data:
            Path(output_dir).mkdir(exist_ok=True)
            base_filename = url.split('/')[-2]
            
            # Save speeches
            if speeches:
                speeches_path = Path(output_dir) / f"{base_filename}_speeches.json"
                with open(speeches_path, 'w', encoding='utf-8') as f:
                    json.dump(speeches, f, ensure_ascii=False, indent=2)
            
            # Save speakers list data
            if speakers_data:
                speakers_path = Path(output_dir) / f"{base_filename}_speakers.json"
                with open(speakers_path, 'w', encoding='utf-8') as f:
                    json.dump(speakers_data, f, ensure_ascii=False, indent=2)
                
        return speeches, speakers_data
        
    except Exception as e:
        print(f"Error in get_transcript: {e}")
        raise
        
    finally:
        context.close()
        browser.close()
        playwright.stop()

def process_all_sessions(csv_path='sweden/sessions.csv'):
    """Process all sessions from CSV file"""
    df = pd.read_csv(csv_path)
    
    for url in df['url']:
        try:
            print(f"Processing {url}")
            speeches, speakers_data = get_transcript(url)
            print(f"Extracted {len(speeches)} speeches and {len(speakers_data)} speaker entries")
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue

def test_single_url():
    """Test transcript extraction with a single URL"""
    test_url = "https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/utgiftsomrade-8-migration_hc01sfu4/"
    
    try:
        print(f"Processing test URL: {test_url}")
        speeches, speakers_data = get_transcript(test_url)
        
        if speeches or speakers_data:
            # Create output directory if it doesn't exist
            Path('test_results').mkdir(exist_ok=True)
            
            # Save speeches to CSV
            if speeches:
                speeches_df = pd.DataFrame(speeches)
                speeches_path = Path('test_results') / 'test_transcript.csv'
                speeches_df.to_csv(speeches_path, index=False, encoding='utf-8')
                print(f"Speeches saved to {speeches_path}")
            
            # Save speakers data to CSV
            if speakers_data:
                speakers_df = pd.DataFrame(speakers_data)
                speakers_path = Path('test_results') / 'test_speakers.csv'
                speakers_df.to_csv(speakers_path, index=False, encoding='utf-8')
                print(f"Speakers data saved to {speakers_path}")
            
            print(f"Successfully extracted {len(speeches)} speeches and {len(speakers_data)} speaker entries")
            
    except Exception as e:
        print(f"Error processing URL: {e}")

if __name__ == "__main__":
    # process_all_sessions()  # Comment out the original function
    test_single_url()  # Run the test function instead
