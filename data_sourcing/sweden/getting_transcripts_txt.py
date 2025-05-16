from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def setup_stealth_browser():
    """Initialize playwright browser with stealth mode"""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    # Add stealth mode script
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return playwright, browser, context

def extract_transcript_data(page):
    """Extract speech data and format it for TXT output"""
    speeches = []
    
    # Get timing data first
    timing_data = {}
    speakers_list = page.query_selector('#speakers-list')
    if speakers_list:
        for item in speakers_list.query_selector_all('li'):
            link = item.query_selector('a')
            if not link:
                continue
                
            href = link.get_attribute('href')
            time_element = link.query_selector('time')
            if href and time_element:
                pos = href.split('pos=')[1].split('&')[0]
                timing_data[pos] = time_element.inner_text()
    
    # Extract speeches
    content_div = page.query_selector('#Accordion-video-protocol-0-content')
    if not content_div:
        return []
        
    for speech_div in content_div.query_selector_all('.sc-5be275a0-1'):
        try:
            # Extract speaker info
            speaker_link = speech_div.query_selector('.sc-d9f50bcf-0')
            speaker_name = speaker_link.inner_text().strip() if speaker_link else "Unknown Speaker"
            
            # Extract speech number and title
            title = speech_div.query_selector('h3')
            speech_num = title.inner_text() if title else ""
            
            # Extract content
            content_div = speech_div.query_selector('.sc-7f1468f0-0')
            content = content_div.inner_text().strip() if content_div else ""
            
            # Extract video position and timestamp
            pos_link = speech_div.query_selector('.sc-51573eba-1 a')
            if pos_link:
                href = pos_link.get_attribute('href')
                pos = href.split('pos=')[1] if 'pos=' in href else None
                timestamp = timing_data.get(pos, "")
            else:
                pos = ""
                timestamp = ""

            speeches.append({
                'speaker': speaker_name,
                'speech_number': speech_num,
                'content': content,
                'video_position': pos,
                'timestamp': timestamp
            })
            
        except Exception as e:
            print(f"Error extracting speech: {e}")
            continue
            
    return speeches

def format_txt_transcript(speeches):
    """Format speeches into the specified TXT format"""
    txt_content = ""
    for speech in speeches:
        txt_content += "[SPEECH]\n"
        txt_content += f"Speaker: {speech['speaker']}\n"
        txt_content += f"Time: {speech['timestamp']}\n"
        txt_content += f"Position: {speech['video_position']}\n"
        txt_content += f"Reference: {speech['speech_number']}\n"
        txt_content += "\nContent:\n"
        txt_content += speech['content']
        txt_content += "\n\n" + "="*80 + "\n\n"
    return txt_content

def get_transcript_txt(session_url: str, output_dir: str = 'transcripts') -> str:
    """
    Get transcript for a session URL and save it as TXT file.
    
    Args:
        session_url: URL of the parliamentary session
        output_dir: Directory to save the transcript
        
    Returns:
        str: Path to the saved transcript file
    """
    playwright, browser, context = setup_stealth_browser()
    
    try:
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Setup page
        page = context.new_page()
        page.goto(session_url)
        
        # Wait for and click transcript button if needed
        button_selector = '#Accordion-video-protocol-0-button'
        page.wait_for_selector(button_selector, timeout=10000)
        button = page.query_selector(button_selector)
        
        if button.get_attribute('aria-expanded') != 'true':
            button.click()
            
        # Wait for content
        page.wait_for_selector('#Accordion-video-protocol-0-content', 
                             state='visible', 
                             timeout=10000)
        time.sleep(2)
        
        # Extract and format transcript
        speeches = extract_transcript_data(page)
        if not speeches:
            raise Exception("No speeches found in transcript")
            
        txt_content = format_txt_transcript(speeches)
        
        # Save to file
        base_filename = session_url.split('/')[-2]
        output_path = Path(output_dir) / f"{base_filename}.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
            
        return str(output_path)
        
    except Exception as e:
        print(f"Error getting transcript: {e}")
        raise
        
    finally:
        context.close()
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    # Example usage
    test_url = "https://www.riksdagen.se/sv/webb-tv/video/debatt-om-forslag/utgiftsomrade-8-migration_hc01sfu4/"
    try:
        output_file = get_transcript_txt(test_url)
        print(f"Transcript saved to: {output_file}")
    except Exception as e:
        print(f"Failed to get transcript: {e}") 