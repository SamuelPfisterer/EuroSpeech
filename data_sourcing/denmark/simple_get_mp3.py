from playwright.async_api import async_playwright
import asyncio
import aiohttp
import csv
import random

async def extract_src_url(page):
    """Extract src_url from the video element"""
    try:
        print("Searching for video player...")
        
        # Find the outer iframe (mobiltv)
        print("Looking for mobiltv iframe...")
        outer_iframe = await page.wait_for_selector('iframe[src*="mobiltv.ft.dk"]', timeout=10000)
        if not outer_iframe:
            print("No mobiltv iframe found")
            return None
            
        # Get outer iframe content
        outer_frame = await outer_iframe.content_frame()
        if not outer_frame:
            print("Could not get content frame for mobiltv iframe")
            return None
        
        # Wait for frame to load
        await asyncio.sleep(3)
        
        # Find Kaltura iframe within the outer frame
        print("Looking for Kaltura iframe...")
        inner_iframe = await outer_frame.wait_for_selector('iframe[id*="kaltura_player"]', timeout=10000)
        if not inner_iframe:
            print("No Kaltura iframe found")
            return None
        
        # Get Kaltura iframe content
        kaltura_frame = await inner_iframe.content_frame()
        if not kaltura_frame:
            print("Could not get content frame for Kaltura iframe")
            return None
        
        # Wait for frame to load
        await asyncio.sleep(3)
        
        # Find video element
        print("Looking for video element...")
        video = await kaltura_frame.wait_for_selector('video', timeout=10000)
        if not video:
            print("No video element found")
            return None
        
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
        
    print(f"Following redirects for: {src_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Set headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Referer': 'https://www.ft.dk/'
            }
            
            # Follow redirects
            async with session.get(src_url, headers=headers, allow_redirects=True) as response:
                final_url = str(response.url)
                print(f"Final URL after redirects: {final_url}")
                return final_url
    
    except Exception as e:
        print(f"Error following redirects: {e}")
        return None

async def main():
    # Hardcoded URL to test
    urls = select_random_links("links/danish_parliament_meetings_full_links.csv")
    
    async with async_playwright() as playwright:
        # Launch browser
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        for url in urls:
            try:
                # Navigate to the URL
                print(f"Processing URL: {url}")
                print("Loading page...")
                await page.goto(url, timeout=60000)
                
                # Wait for page to load
                await asyncio.sleep(5)
                
                # Extract src_url
                src_url = await extract_src_url(page)
                
                # Follow redirects to get MP3 URL
                if src_url:
                    mp3_url = await follow_redirect(src_url)
                    print("\n=== RESULTS ===")
                    print(f"Original URL: {url}")
                    print(f"Source URL: {src_url}")
                    print(f"MP3 URL: {mp3_url}")
                else:
                    print("Failed to extract source URL")
            
            except Exception as e:
                print(f"Error: {e}")
        
        await browser.close()

def select_random_links(csv_file, num_links=5):
    """Select random links from the specified CSV file."""
    links = []

    # Read the CSV file
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'generic_video_link' in row and row['generic_video_link']:
                links.append(row['generic_video_link'])

    # Select random links
    selected_links = random.sample(links, min(num_links, len(links)))
    return selected_links

# Specify the path to your CSV file
csv_file_path = 'links/danish_parliament_meetings_full_links.csv'

# Get 5 random links
random_links = select_random_links(csv_file_path)
print("Selected Random Links:")
for link in random_links:
    print(link)

if __name__ == "__main__":
    asyncio.run(main()) 