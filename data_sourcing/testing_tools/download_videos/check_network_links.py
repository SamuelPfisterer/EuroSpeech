from playwright.sync_api import sync_playwright
import re
import json
from datetime import datetime
import time

def monitor_network_traffic(url):
    """Monitor network traffic for m3u8 streams using Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for headless mode
        context = browser.new_context()
        
        # Create a page and start monitoring network
        page = context.new_page()
        m3u8_urls = set()
        
        # Listen to network requests
        def handle_request(request):
            url = request.url
            if '.m3u8' in url:
                m3u8_urls.add(url)
                print(f"Found m3u8 URL: {url}")
                
                # Try to extract pattern components
                pattern = r'https://ftlive\.streaming\.ft\.dk/vod/_definst_/mp4:(\d{4})/(\d{4}_\d{2}_\d{2}).*?(\d+)_h264\.mp4/playlist\.m3u8'
                match = re.match(pattern, url)
                
                if match:
                    year, date_str, video_id = match.groups()
                    print("\nURL Pattern found!")
                    print(f"Year: {year}")
                    print(f"Date string: {date_str}")
                    print(f"Video ID: {video_id}")

        page.on("request", handle_request)

        try:
            print("Loading page and monitoring network traffic...")
            page.goto(url)
            
            # Try to click the play button (adjust selectors as needed)
            try:
                # Wait for video player and click
                page.wait_for_selector('.flowplayer, .video-js', timeout=5000)
                page.click('.flowplayer, .video-js')
            except Exception as e:
                print(f"Couldn't find play button, but continuing to monitor traffic... ({str(e)})")
            
            # Monitor for a few seconds
            time.sleep(10)
            
            # Create template from found URLs
            template = None
            if m3u8_urls:
                sample_url = next(iter(m3u8_urls))
                template = "https://ftlive.streaming.ft.dk/vod/_definst_/mp4:{year}/{date}_13_00_F_{video_id}_h264.mp4/playlist.m3u8"
                print(f"\nTemplate for future URLs:")
                print(template)
            
            return template, list(m3u8_urls)
            
        finally:
            browser.close()

def generate_video_url(template, video_id, date_str):
    """Generate video URL from template and parameters"""
    try:
        # Parse date string (assuming format: YYYY-MM-DD)
        date = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date.strftime('%Y_%m_%d')
        year = date.strftime('%Y')
        
        # Generate URL
        url = template.format(
            year=year,
            date=formatted_date,
            video_id=video_id
        )
        return url
    except Exception as e:
        print(f"Error generating URL: {str(e)}")
        return None

def verify_m3u8_url(url):
    """Verify if the m3u8 URL is accessible"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        
        try:
            response = page.request.get(url)
            if response.ok:
                content = response.text()
                if '#EXTM3U' in content:  # Basic check for m3u8 content
                    return True
            return False
        except Exception as e:
            print(f"Error verifying URL: {str(e)}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    # Install playwright browsers first time: python -m playwright install
    
    # Test URL
    url = "https://www.ft.dk/aktuelt/webtv/video/20101/salen/108.aspx"
    
    print("Analyzing video page...")
    template, found_urls = monitor_network_traffic(url)
    
    if template:
        print("\nFound URLs:")
        for url in found_urls:
            print(f"- {url}")
            
        print("\nTesting URL generation:")
        # Test generating a new URL
        test_url = generate_video_url(
            template,
            video_id="109",
            date_str="2024-03-14"
        )
        print(f"Generated test URL: {test_url}")
        
        # Verify the generated URL
        if test_url:
            print("\nVerifying generated URL...")
            if verify_m3u8_url(test_url):
                print("✓ URL is valid and accessible")
            else:
                print("✗ URL is not accessible")
    else:
        print("No m3u8 URLs found")