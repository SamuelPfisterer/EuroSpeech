from playwright.async_api import async_playwright
import asyncio
import time
import random
import csv
from datetime import datetime
from pathlib import Path
import re
import aiohttp
import argparse

async def random_delay(min_seconds=1, max_seconds=3):
    """Add random delay between requests to mimic human behavior"""
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))

async def setup_browser(playwright):
    """Setup browser with stealth configurations"""
    browser = await playwright.chromium.launch(
        headless=False,  # Run in non-headless mode for debugging
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-web-security',  # Add this to handle potential CORS issues
            '--disable-features=IsolateOrigins',
            '--disable-site-isolation-trials'
        ]
    )
    
    # Create context with stealth settings
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        java_script_enabled=True,
        bypass_csp=True,
        ignore_https_errors=True,
        extra_http_headers={
            'Accept-Language': 'da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
    )
    
    # Add stealth scripts
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Add more stealth
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        Object.defineProperty(navigator, 'languages', {
            get: () => ['da-DK', 'da', 'en-US', 'en']
        });
    """)
    
    return browser, context

async def extract_src_url(page):
    """Extract src_url from the video element"""
    try:
        print("\nSearching for video player...")
        
        # First locate the outer iframe (mobiltv)
        print("Looking for mobiltv iframe...")
        outer_iframe = None
        outer_selectors = [
            '#mobilVideoPlayer1',
            'iframe[src*="mobiltv.ft.dk"]',
            'iframe.video-player-iframe'
        ]
        
        for selector in outer_selectors:
            try:
                print(f"Trying outer selector: {selector}")
                outer_iframe = await page.wait_for_selector(selector, timeout=5000)
                if outer_iframe:
                    print(f"Found outer iframe with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not outer_iframe:
            print("No mobiltv iframe found with any selector")
            return None
            
        # Get outer iframe content frame
        print("Getting mobiltv iframe content...")
        outer_frame = await outer_iframe.content_frame()
        if not outer_frame:
            print("Could not get content frame for mobiltv iframe")
            return None
        
        # Wait for frame to load
        await random_delay(2, 3)
        
        # Now look for Kaltura iframe within the outer frame
        print("Looking for Kaltura iframe inside mobiltv frame...")
        inner_iframe = None
        inner_selectors = [
            'iframe[id*="kaltura_player"]',
            'iframe[src*="kaltura"]',
            'iframe[src*="cdnapisec"]'
        ]
        
        for selector in inner_selectors:
            try:
                print(f"Trying inner selector: {selector}")
                inner_iframe = await outer_frame.wait_for_selector(selector, timeout=5000)
                if inner_iframe:
                    print(f"Found Kaltura iframe with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not inner_iframe:
            print("No Kaltura iframe found in mobiltv frame")
            return None
        
        # Get Kaltura iframe content frame
        print("Getting Kaltura iframe content...")
        kaltura_frame = await inner_iframe.content_frame()
        if not kaltura_frame:
            print("Could not get content frame for Kaltura iframe")
            return None
        
        # Wait for frame to load
        await random_delay(2, 3)
        
        # Look for video element in Kaltura frame
        print("Looking for video element in Kaltura frame...")
        video = None
        video_selectors = [
            'video.persistentNativePlayer',
            'video#pid_kaltura_player',
            'video[id*="kaltura_player"]',
            'video'  # Generic fallback
        ]
        
        for selector in video_selectors:
            try:
                print(f"Trying video selector: {selector}")
                video = await kaltura_frame.wait_for_selector(selector, timeout=5000)
                if video:
                    print(f"Found video element with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not video:
            print("No video element found in Kaltura frame")
            return None
        
        print("Found video element, extracting src attribute...")
        # Extract src attribute
        src_url = await video.get_attribute('src')
        
        if not src_url:
            print("No src attribute found on video element")
            return None
            
        print(f"Found src_url: {src_url}")
        return src_url
    
    except Exception as e:
        print(f"Error extracting video src: {e}")
        return None

async def follow_redirect(src_url):
    """Follow redirects to get the final MP3 URL"""
    if not src_url:
        return None
        
    print(f"\nFollowing redirects for: {src_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Set headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.ft.dk/'
            }
            
            # Follow redirects
            async with session.get(src_url, headers=headers, allow_redirects=True) as response:
                final_url = str(response.url)
                print(f"Final URL after redirects: {final_url}")
                
                # Check if it's an MP3 URL
                if final_url.endswith('.mp3') or 'audio' in final_url:
                    print("Successfully found MP3 URL!")
                    return final_url
                else:
                    print("Final URL is not an MP3 link")
                    return final_url  # Return anyway, might be useful
    
    except Exception as e:
        print(f"Error following redirects: {e}")
        return None

def save_results(url, src_url, mp3_url, output_file):
    """Save the extracted URLs to a CSV file"""
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Define whether we need to write headers (only for new files)
    write_headers = not output_file.exists()
    
    # Define field names
    fieldnames = ['original_url', 'src_url', 'mp3_url', 'timestamp']
    
    # Prepare data
    data = {
        'original_url': url,
        'src_url': src_url,
        'mp3_url': mp3_url,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Open in append mode with UTF-8 encoding
    with open(output_file, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write headers only for new files
        if write_headers:
            writer.writeheader()
        
        # Write the result
        writer.writerow(data)
    
    print(f"\nResults appended to: {output_file}")

async def process_url(url, output_file):
    """Process a single URL to extract src_url and MP3 link"""
    async with async_playwright() as playwright:
        browser, context = await setup_browser(playwright)
        
        try:
            print(f"\nProcessing URL: {url}")
            
            # Create a new page
            page = await context.new_page()
            
            # Navigate to the URL
            print("Loading page...")
            try:
                await page.goto(url, wait_until='load', timeout=60000)
            except Exception as e:
                print(f"Initial load attempt failed: {e}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for dynamic content
            print("Waiting for dynamic content...")
            await random_delay(3, 5)
            
            # Extract src_url
            src_url = await extract_src_url(page)
            
            # Follow redirects to get MP3 URL
            mp3_url = None
            if src_url:
                mp3_url = await follow_redirect(src_url)
            
            # Save results
            if src_url or mp3_url:
                save_results(url, src_url, mp3_url, output_file)
            else:
                print("No URLs extracted, nothing to save")
            
        except Exception as e:
            print(f"Error processing URL: {e}")
        
        finally:
            await browser.close()

async def process_csv(csv_file, output_file, start_idx=0, end_idx=None):
    """Process URLs from a CSV file"""
    try:
        # Read URLs from CSV
        urls = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'generic_video_link' in row and row['generic_video_link']:
                    urls.append(row['generic_video_link'])
        
        # Apply index limits
        if end_idx is None:
            end_idx = len(urls)
        
        urls = urls[start_idx:end_idx]
        print(f"Processing {len(urls)} URLs from index {start_idx} to {end_idx-1}")
        
        # Process each URL
        for i, url in enumerate(urls):
            print(f"\nProcessing URL {i+start_idx}/{end_idx-1}: {url}")
            await process_url(url, output_file)
            # Add delay between requests
            if i < len(urls) - 1:
                await random_delay(2, 5)
    
    except Exception as e:
        print(f"Error processing CSV file: {e}")

async def main_async(args):
    """Async main function"""
    # Create output file path
    output_dir = Path('output')
    output_file = output_dir / 'mp3_links.csv'
    
    if args.url:
        # Process a single URL
        await process_url(args.url, output_file)
    elif args.csv_file:
        # Process URLs from CSV
        await process_csv(args.csv_file, output_file, args.start_idx, args.end_idx)
    else:
        print("No URL or CSV file specified. Use --url or --csv_file argument.")

def main():
    """Entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract MP3 links from Danish Parliament videos')
    parser.add_argument('--url', type=str, help='URL of a single video page to process')
    parser.add_argument('--csv_file', type=str, help='CSV file containing video links to process')
    parser.add_argument('--start_idx', type=int, default=0, help='Starting index in CSV file')
    parser.add_argument('--end_idx', type=int, help='Ending index in CSV file')
    
    args = parser.parse_args()
    
    # Run async main
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main() 