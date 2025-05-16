from playwright.async_api import async_playwright
import asyncio
import time
import random
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import re

async def random_delay(min_seconds=1, max_seconds=3):
    """Add random delay between requests to mimic human behavior"""
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))

async def setup_stealth_browser(playwright, username: str, password: str):
    """Setup browser with stealth configurations and proxy"""
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
        #,
        #proxy={
        #    'server': 'http://gate.smartproxy.com:7000',
        #    'username': username,
        #    'password': password
        #}
        #
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

async def extract_kaltura_info(page) -> Dict:
    """Extract Kaltura video information from the page"""
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
            # Save outer frame content for debugging
            try:
                frame_content = await outer_frame.content()
                debug_dir = Path("output/debug_content")
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                with open(debug_dir / f"mobiltv_frame_{timestamp}.html", 'w', encoding='utf-8') as f:
                    f.write(frame_content)
                print("Saved mobiltv frame content for debugging")
            except Exception as e:
                print(f"Error saving frame content: {e}")
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
            # Save Kaltura frame content for debugging
            try:
                frame_content = await kaltura_frame.content()
                debug_dir = Path("output/debug_content")
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                with open(debug_dir / f"kaltura_frame_{timestamp}.html", 'w', encoding='utf-8') as f:
                    f.write(frame_content)
                print("Saved Kaltura frame content for debugging")
            except Exception as e:
                print(f"Error saving frame content: {e}")
            return None
        
        print("Found video element, extracting attributes...")
        # Extract attributes
        entry_id = await video.get_attribute('kentryid')
        partner_id = await video.get_attribute('kpartnerid')
        ui_config_id = await video.get_attribute('kuiconfid')
        widget_id = await video.get_attribute('kwidgetid')
        src_url = await video.get_attribute('src')
        
        # Extract flavor_id from src URL
        flavor_id = None
        if src_url:
            # Try both flavorId and flavorIds patterns
            flavor_match = re.search(r'flavor(?:Id|Ids)/([^/]+)/', src_url)
            if flavor_match:
                flavor_id = flavor_match.group(1)
                print(f"Found flavor_id: {flavor_id}")
            else:
                print("No flavor_id found in URL. URL was:", src_url)
        
        # Construct direct m3u8 URL
        direct_m3u8_url = None
        if all([partner_id, entry_id, flavor_id]):
            direct_m3u8_url = (
                f"https://cdnapisec.kaltura.com/p/{partner_id}/sp/{partner_id}00/"
                f"playManifest/entryId/{entry_id}/flavorIds/{flavor_id}/"
                f"format/applehttp/protocol/https/a.m3u8"
            )
        
        result = {
            'session_url': page.url,
            'entry_id': entry_id,
            'partner_id': partner_id,
            'ui_config_id': ui_config_id,
            'widget_id': widget_id,
            'src_url': src_url,
            'flavor_id': flavor_id,
            'direct_m3u8_url': direct_m3u8_url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print("\nExtracted video information:")
        for key, value in result.items():
            print(f"{key}: {value}")
        
        return result
    
    except Exception as e:
        print(f"Error extracting video info: {e}")
        # Save all frame contents for debugging
        try:
            debug_dir = Path("output/debug_content")
            debug_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save main page
            content = await page.content()
            with open(debug_dir / f"main_page_{timestamp}.html", 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Try to save mobiltv iframe content
            outer_iframe = await page.query_selector('iframe[src*="mobiltv.ft.dk"]')
            if outer_iframe:
                outer_frame = await outer_iframe.content_frame()
                if outer_frame:
                    frame_content = await outer_frame.content()
                    with open(debug_dir / f"mobiltv_frame_{timestamp}.html", 'w', encoding='utf-8') as f:
                        f.write(frame_content)
            
            print(f"Saved debug content to output/debug_content/")
        except Exception as debug_error:
            print(f"Error saving debug content: {debug_error}")
        return None

def save_results(result: Dict, output_file: Path):
    """Save the extracted information to a CSV file"""
    if not result:
        return
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Define whether we need to write headers (only for new files)
    write_headers = not output_file.exists()
    
    # Define field names in a specific order
    fieldnames = [
        'session_url',
        'entry_id',
        'partner_id',
        'ui_config_id',
        'widget_id',
        'src_url',
        'flavor_id',
        'direct_m3u8_url',
        'timestamp'
    ]
    
    # Open in append mode with UTF-8 encoding
    with open(output_file, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write headers only for new files
        if write_headers:
            writer.writeheader()
        
        # Write the result
        writer.writerow(result)
    
    print(f"\nResults appended to: {output_file}")

async def process_session(url: str, output_file: Path) -> None:
    """Process a single session page"""
    async with async_playwright() as playwright:
        browser, context = await setup_stealth_browser(playwright, username = 'sph4b47do7', password = 'fsv5fKD+wvTzLwt628')
        
        try:
            print(f"\nProcessing URL: {url}")
            
            # Create a new page
            page = await context.new_page()
            
            # Navigate to the URL with more lenient settings
            print("Loading page...")
            try:
                # First try with load event
                await page.goto(url, wait_until='load', timeout=60000)
            except Exception as e:
                print(f"Initial load attempt failed: {e}")
                # If that fails, try with domcontentloaded
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait a bit for dynamic content
            print("Waiting for dynamic content...")
            await random_delay(3, 5)
            
            # Make sure the page is fully loaded
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
            except:
                pass  # Continue even if this times out
            
            # Extract Kaltura information
            result = await extract_kaltura_info(page)
            
            # Save results
            if result:
                save_results(result, output_file)
            
        except Exception as e:
            print(f"Error processing session: {e}")
            # Save page state for debugging
            try:
                debug_dir = Path("output/debug_content")
                debug_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Take screenshot
                await page.screenshot(path=debug_dir / f"error_screenshot_{timestamp}.png", full_page=True)
                
                # Save page content
                content = await page.content()
                with open(debug_dir / f"error_page_{timestamp}.html", 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Saved error state to output/debug_content/")
            except Exception as debug_error:
                print(f"Error saving debug content: {debug_error}")
        
        finally:
            await browser.close()

def main():
    """Entry point"""
    # Example URL - replace with actual URL
    url = "https://www.ft.dk/aktuelt/webtv/video/20101/salen/100.aspx"
    
    # Create output file path
    output_dir = Path('output')
    output_file = output_dir / 'kaltura_info.csv'
    
    asyncio.run(process_session(url, output_file))

if __name__ == "__main__":
    main() 