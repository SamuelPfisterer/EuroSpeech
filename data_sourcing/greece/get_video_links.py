from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
from tqdm import tqdm

def get_mp4_link(page, video_url):
    try:
        # Convert relative URL to absolute URL if needed
        if video_url.startswith('/'):
            video_url = f"https://www.hellenicparliament.gr{video_url}"
            
        print(f"\nNavigating to URL: {video_url}")
        
        try:
            # Navigate directly to the full URL including fragment
            for attempt in range(3):  # Try up to 3 times
                try:
                    response = page.goto(video_url, wait_until='networkidle', timeout=30000)
                    if response and response.ok:
                        print(f"Successfully loaded page (attempt {attempt + 1})")
                        page.wait_for_load_state('networkidle')
                        current_url = page.url
                        print(f"Current URL: {current_url}")
                        break
                    else:
                        print(f"Failed to load page (attempt {attempt + 1})")
                        if attempt < 2:
                            time.sleep(5)
                except Exception as e:
                    print(f"Navigation error (attempt {attempt + 1}): {e}")
                    if attempt < 2:
                        time.sleep(5)
            
            if not response or not response.ok:
                print(f"Failed to load page after 3 attempts")
                return None
            
            # Wait for video element and try different methods to get the source
            try:
                page.wait_for_selector('video', timeout=20000)
                print("Video element found on page")
            except Exception as e:
                print(f"No video element found: {e}")
                # Try to print the page content for debugging
                print("\nPage content:")
                print(page.content()[:500])  # First 500 chars
                return None
                
            # Method 1: Try to get source via JavaScript
            mp4_link = page.evaluate('''() => {
                const video = document.querySelector('video');
                if (!video) return null;
                const source = video.querySelector('source[type="video/mp4"]');
                return source ? source.src : null;
            }''')
            
            if not mp4_link:
                # Method 2: Try to get source from video element directly
                mp4_link = page.evaluate('''() => {
                    const video = document.querySelector('video');
                    return video ? video.currentSrc : null;
                }''')
            
            if mp4_link:
                # Convert relative URL to absolute if needed
                if mp4_link.startswith('/'):
                    mp4_link = f"https://www.hellenicparliament.gr{mp4_link}"
                print(f"Successfully found MP4 link via JavaScript: {mp4_link}")
                return mp4_link
                
            # If JavaScript methods fail, try parsing the HTML
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Print the entire video element for debugging
            video_element = soup.find('video')
            if video_element:
                print("\nFound video element in HTML:")
                print(video_element.prettify())
            
            # Try to find any elements that might contain video URLs
            potential_links = page.evaluate('''() => {
                const links = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.src && el.src.includes('.mp4')) links.push(el.src);
                    if (el.href && el.href.includes('.mp4')) links.push(el.href);
                    if (el.getAttribute('data-src') && el.getAttribute('data-src').includes('.mp4')) 
                        links.push(el.getAttribute('data-src'));
                });
                return links;
            }''')
            
            if potential_links:
                print("\nFound potential video links:", potential_links)
                return potential_links[0]  # Return the first found MP4 link
                
            print("No MP4 link found through any method")
            return None
            
        except Exception as e:
            print(f"Error while extracting video source: {e}")
            return None
            
    except Exception as e:
        print(f"Error processing {video_url}: {str(e)}")
        print("Full error:", e)
        return None

def main():
    # Read the session links CSV
    sessions = []
    with open('session_links.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sessions = list(reader)
    
    # Take just the first 5 sessions that have video links
    test_sessions = []
    for session in sessions:
        if session['video_links']:
            test_sessions.append(session)
            if len(test_sessions) == 5:
                break
    
    print(f"\nTesting with {len(test_sessions)} sessions:")
    for session in test_sessions:
        print(f"Date: {session['date']}, Video links: {session['video_links']}")
    
    # Prepare output data
    output_data = []
    
    with sync_playwright() as p:
        # Process test sessions
        with tqdm(total=len(test_sessions), desc="Processing videos") as pbar:
            for session in test_sessions:
                print(f"\nProcessing session from {session['date']}:")
                video_links = session['video_links'].split(';') if session['video_links'] else []
                
                if video_links:
                    mp4_links = []
                    for video_url in video_links:
                        if video_url:  # Skip empty strings
                            print(f"  Processing video URL: {video_url}")
                            
                            # Create new browser and context for each video URL
                            browser = p.chromium.launch(
                                headless=False,
                                args=[
                                    '--disable-blink-features=AutomationControlled',
                                    '--disable-infobars',
                                    '--window-size=1920,1080',
                                    '--start-maximized'
                                ]
                            )
                            
                            context = browser.new_context(
                                viewport={'width': 1920, 'height': 1080},
                                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                                java_script_enabled=True,
                                ignore_https_errors=True,
                                extra_http_headers={
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                                }
                            )
                            
                            # Add stealth scripts
                            context.add_init_script("""
                                Object.defineProperty(navigator, 'webdriver', {
                                    get: () => undefined
                                });
                                window.chrome = { runtime: {} };
                                Object.defineProperty(navigator, 'plugins', {
                                    get: () => [1, 2, 3, 4, 5]
                                });
                                Object.defineProperty(navigator, 'languages', {
                                    get: () => ['en-US', 'en']
                                });
                            """)
                            
                            page = context.new_page()
                            
                            try:
                                mp4_link = get_mp4_link(page, video_url)
                                if mp4_link:
                                    print(f"  Found MP4 link: {mp4_link}")
                                    mp4_links.append(mp4_link)
                                else:
                                    print("  No MP4 link found!")
                            finally:
                                browser.close()
                                
                            time.sleep(3)  # Wait between videos
                            
                    session['mp4_links'] = ';'.join(mp4_links) if mp4_links else ''
                else:
                    session['mp4_links'] = ''
                    
                output_data.append(session)
                pbar.update(1)
                time.sleep(2)  # Added wait between sessions
        
    # Print results
    print("\nResults:")
    for session in output_data:
        print(f"\nDate: {session['date']}")
        print(f"Original video links: {session['video_links']}")
        print(f"Found MP4 links: {session['mp4_links']}")
    
    # Write the test results to a new CSV
    with open('test_session_links_with_mp4.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = list(output_data[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_data)

if __name__ == "__main__":
    main()
