import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import csv
import os
import time
from tqdm.asyncio import tqdm as async_tqdm

# --- ASYNC VERSION ---

async def get_mp4_link(page, video_url):
    try:
        # Convert relative URL to absolute URL if needed
        if video_url.startswith('/'):
            video_url = f"https://www.hellenicparliament.gr{video_url}"
        print(f"\nNavigating to URL: {video_url}")
        try:
            for attempt in range(3):
                try:
                    response = await page.goto(video_url, wait_until='networkidle', timeout=30000)
                    if response and response.ok:
                        print(f"Successfully loaded page (attempt {attempt + 1})")
                        await page.wait_for_load_state('networkidle')
                        current_url = page.url
                        print(f"Current URL: {current_url}")
                        break
                    else:
                        print(f"Failed to load page (attempt {attempt + 1})")
                        if attempt < 2:
                            await asyncio.sleep(5)
                except Exception as e:
                    print(f"Navigation error (attempt {attempt + 1}): {e}")
                    if attempt < 2:
                        await asyncio.sleep(5)
            if not response or not response.ok:
                print(f"Failed to load page after 3 attempts")
                return None
            try:
                await page.wait_for_selector('video', timeout=20000)
                print("Video element found on page")
            except Exception as e:
                print(f"No video element found: {e}")
                print("\nPage content:")
                print((await page.content())[:500])
                return None
            mp4_link = await page.evaluate('''() => {
                const video = document.querySelector('video');
                if (!video) return null;
                const source = video.querySelector('source[type=\"video/mp4\"]');
                return source ? source.src : null;
            }''')
            if not mp4_link:
                mp4_link = await page.evaluate('''() => {
                    const video = document.querySelector('video');
                    return video ? video.currentSrc : null;
                }''')
            if mp4_link:
                if mp4_link.startswith('/'):
                    mp4_link = f"https://www.hellenicparliament.gr{mp4_link}"
                print(f"Successfully found MP4 link via JavaScript: {mp4_link}")
                return mp4_link
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            video_element = soup.find('video')
            if video_element:
                print("\nFound video element in HTML:")
                print(video_element.prettify())
            potential_links = await page.evaluate('''() => {
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
                return potential_links[0]
            print("No MP4 link found through any method")
            return None
        except Exception as e:
            print(f"Error while extracting video source: {e}")
            return None
    except Exception as e:
        print(f"Error processing {video_url}: {str(e)}")
        print("Full error:", e)
        return None

def create_expanded_csv():
    # Read the CSV with the mp4 links
    sessions = []
    with open('test_session_links_with_mp4.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sessions = list(reader)
    
    # Prepare output data with separate rows for each video link
    expanded_rows = []
    
    for session in sessions:
        # Get both mp4 links and original video links
        mp4_links = session['mp4_links'].split(';') if session['mp4_links'] else []
        video_links = session['video_links'].split(';') if session['video_links'] else []
        
        # Make sure we have a valid list of links
        mp4_links = [link.strip() for link in mp4_links if link.strip()]
        video_links = [link.strip() for link in video_links if link.strip()]
        
        if mp4_links:  # If there are mp4 links
            # Create a separate row for each mp4 link with its corresponding original video link
            for i, mp4_link in enumerate(mp4_links):
                new_row = session.copy()
                new_row['mp4_link'] = mp4_link
                
                # Assign the corresponding video_link if available
                if i < len(video_links):
                    new_row['video_link'] = video_links[i]
                else:
                    new_row['video_link'] = ''
                
                # Remove the original combined fields
                if 'mp4_links' in new_row:
                    del new_row['mp4_links']
                if 'video_links' in new_row:
                    del new_row['video_links']
                
                expanded_rows.append(new_row)
        else:
            # If no mp4 links, create one row per original video link
            if video_links:
                for video_link in video_links:
                    new_row = session.copy()
                    new_row['mp4_link'] = ''
                    new_row['video_link'] = video_link
                    
                    # Remove the original combined fields
                    if 'mp4_links' in new_row:
                        del new_row['mp4_links']
                    if 'video_links' in new_row:
                        del new_row['video_links']
                    
                    expanded_rows.append(new_row)
            else:
                # If no video links either, keep one row with empty links
                new_row = session.copy()
                new_row['mp4_link'] = ''
                new_row['video_link'] = ''
                
                # Remove the original combined fields
                if 'mp4_links' in new_row:
                    del new_row['mp4_links']
                if 'video_links' in new_row:
                    del new_row['video_links']
                
                expanded_rows.append(new_row)
    
    # Write to the new CSV
    with open('greece_links.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = list(expanded_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expanded_rows)
    
    print(f"Created greece_links.csv with {len(expanded_rows)} rows")

async def process_video_link(context, video_url, stealth_script):
    page = await context.new_page()
    await page.add_init_script(stealth_script)
    mp4_link = await get_mp4_link(page, video_url)
    await page.close()
    return mp4_link

async def main_async():
    # Load already processed links from CSV if it exists
    processed_keys = set()
    output_data = []
    if os.path.exists('test_session_links_with_mp4.csv'):
        with open('test_session_links_with_mp4.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'processed_video_links' in row and row['processed_video_links']:
                    video_links = row['processed_video_links'].split(';')
                    for idx, video_url in enumerate(video_links):
                        processed_keys.add((row.get('date', ''), video_url.strip()))
                elif 'video_links' in row and row['video_links']:
                    video_links = row['video_links'].split(';')
                    for idx, video_url in enumerate(video_links):
                        processed_keys.add((row.get('date', ''), video_url.strip()))
            f.seek(0)
            output_data = list(reader)
    else:
        output_data = []
    # Load sessions
    sessions = []
    with open('session_links.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sessions = list(reader)
    stealth_script = """
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
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )
        num_parallel = 5
        # Prepare all video links to process
        video_tasks = []
        session_map = []  # (session_idx, video_url_idx)
        for session_idx, session in enumerate(sessions):
            if not session['video_links']:
                continue
            video_links = session['video_links'].split(';') if session['video_links'] else []
            for video_url_idx, video_url in enumerate(video_links):
                key = (session.get('date', ''), video_url.strip())
                if video_url.strip() and key not in processed_keys:
                    video_tasks.append((session_idx, video_url_idx, video_url.strip()))
                    session_map.append((session_idx, video_url_idx))
        sem = asyncio.Semaphore(num_parallel)
        async def process_task(session_idx, video_url_idx, video_url):
            async with sem:
                mp4_link = await process_video_link(context, video_url, stealth_script)
                return (session_idx, video_url_idx, video_url, mp4_link)
        # Open CSV for appending
        fieldnames = list(sessions[0].keys()) + ['mp4_links', 'processed_video_links']
        written_keys = set(processed_keys)
        if not os.path.exists('test_session_links_with_mp4.csv'):
            with open('test_session_links_with_mp4.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        for coro in async_tqdm.as_completed([process_task(*task) for task in video_tasks], total=len(video_tasks), desc="Processing videos in parallel"):
            session_idx, video_url_idx, video_url, mp4_link = await coro
            key = (sessions[session_idx].get('date', ''), video_url)
            if key in written_keys:
                continue  # Already written (paranoia)
            session = sessions[session_idx]
            mp4_links = mp4_link if mp4_link else ''
            processed_video_links = video_url
            row = dict(session)
            row['mp4_links'] = mp4_links
            row['processed_video_links'] = processed_video_links
            with open('test_session_links_with_mp4.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)
            written_keys.add(key)
        await browser.close()
    create_expanded_csv()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 