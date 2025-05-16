from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import time
import os

def extract_media_links(page):
    """Extract media links from the REDUX_STATE script tag"""
    script_content = page.evaluate('''() => {
        const scripts = document.getElementsByTagName('script');
        for (const script of scripts) {
            if (script.textContent && script.textContent.includes('REDUX_STATE')) {
                return script.textContent;
            }
        }
        return null;
    }''')
    
    if script_content:
        json_str = script_content.replace('window.REDUX_STATE = ', '').strip()
        try:
            data = json.loads(json_str)
            streams = data.get('data', {}).get('currentEvent', {}).get('streams', {})
            
            return {
                'hls_stream': streams.get('hls', '').replace('//', 'https://'),
                'mp4_video': streams.get('http', ''),
                'audio_stream': streams.get('audio', '').replace('//', 'https://')
            }
        except json.JSONDecodeError:
            print("Failed to parse JSON from script content")
            return None
    return None

def extract_speech_segments_for_section(page):
    """Extract speech segments for the current section"""
    speeches = []
    
    # Wait for speech segments to load
    page.wait_for_selector('.discussion-block', timeout=5000)
    
    # Get all speech segments in this section
    segments = page.query_selector_all('.discussion-block')
    
    for segment in segments:
        try:
            # Get start and end times
            start_time = segment.get_attribute('data-starttime')
            end_time = segment.get_attribute('data-endtime')
            
            # Get speaker info and text
            speaker_element = segment.query_selector('.seek-el')
            speaker_text = speaker_element.inner_text() if speaker_element else ''
            
            # Get speech text
            speech_paragraphs = segment.query_selector_all('p')
            speech_text = ' '.join([p.inner_text() for p in speech_paragraphs])
            
            # Check for between comments
            between_comment = segment.query_selector('.between-comment')
            between_comment_text = None
            if between_comment:
                between_comment_text = between_comment.inner_text()
            
            speeches.append({
                'speaker': speaker_text,
                'start_time': start_time,
                'end_time': end_time,
                'speech_text': speech_text,
                'between_comment': between_comment_text
            })
            
        except Exception as e:
            print(f"Error processing speech segment: {e}")
            continue
    
    return speeches

def extract_all_sections_and_speeches(page):
    """Extract all sections and their corresponding speeches"""
    sections_data = []
    
    # Wait for the topic section to load
    page.wait_for_selector('.ui.container.topic-section')
    
    # Get all topic buttons
    topic_buttons = page.query_selector_all('.ui.grid .one.column.row[role="button"]')
    print(f"Found {len(topic_buttons)} topic sections")
    
    for i, button in enumerate(topic_buttons, 1):
        try:
            # Get section title
            header = button.query_selector('h4.ui.header')
            section_title = header.inner_text() if header else f"Section {i}"
            
            print(f"Processing section: {section_title}")
            
            # Click the button to load the section content
            button.click()
            # Wait for content to load
            page.wait_for_timeout(2000)  # 2 second wait
            
            # Extract speeches for this section
            speeches = extract_speech_segments_for_section(page)
            
            sections_data.append({
                'section_title': section_title,
                'section_number': i,
                'speeches': speeches
            })
            
            print(f"Found {len(speeches)} speeches in section: {section_title}")
            
        except Exception as e:
            print(f"Error processing section {i}: {e}")
            continue
    
    return sections_data

def load_existing_data():
    """Load existing session data if available"""
    data_file = 'finland_sessions_data.json'
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_session_data(data):
    """Save session data to JSON file"""
    data_file = 'finland_sessions_data.json'
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def scrape_session_page(url):
    """Scrape a single session page for all required information"""
    with sync_playwright() as p:
        # Launch browser with specific configuration to appear more like a regular browser
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080'
            ]
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
        )
        
        page = context.new_page()
        
        try:
            # Navigate to the session page
            print(f"Navigating to {url}")
            page.goto(url)
            page.wait_for_load_state('networkidle')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_load_state('load')
            
            # Wait a bit longer for any dynamic content to initialize
            page.wait_for_timeout(5000)
            
            # Extract media links
            print("Extracting media links...")
            media_links = extract_media_links(page)
            
            # Extract all sections and their speeches
            print("Extracting sections and speeches...")
            sections_data = extract_all_sections_and_speeches(page)
            
            # Get session ID from URL
            session_id = url.split('/')[-1]
            
            # Load existing data
            all_sessions_data = load_existing_data()
            
            # Create session data structure
            session_data = {
                'url': url,
                'scrape_time': datetime.now().isoformat(),
                'media_links': media_links,
                'sections': sections_data
            }
            
            # Add or update session data
            all_sessions_data[session_id] = session_data
            
            # Save updated data
            save_session_data(all_sessions_data)
            
            total_speeches = sum(len(section['speeches']) for section in sections_data)
            print(f"Successfully scraped session {session_id}")
            print(f"Found {len(sections_data)} sections with {total_speeches} total speeches")
            return True
            
        except Exception as e:
            print(f"Error scraping session: {e}")
            return False
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    # Example usage
    session_url = "https://verkkolahetys.eduskunta.fi/fi/taysistunnot/taysistunto-125-2024"
    scrape_session_page(session_url) 