import asyncio
from playwright.async_api import async_playwright
import csv
from pathlib import Path
import time
from tqdm import tqdm
import asyncio
from typing import List, Dict

async def extract_video_links(page, url: str) -> List[Dict]:
    video_links = []
    
    # Try the new format first (icon-link-list)
    visible_links = await page.query_selector_all('ul.icon-link-list li a.link-video')
    if visible_links:
        for link in visible_links:
            href = await link.get_attribute('href')
            span = await link.query_selector('span')
            text = await span.inner_text() if span else ''
            if href:
                video_links.append({
                    'url': f"https://www.stortinget.no{href}",
                    'type': text,
                    'source_page': url,
                    'format': 'new'
                })
    
    # If no links found, try the old format (minutes-navigation-bar-react)
    if not video_links:
        old_links = await page.query_selector_all('div.minutes-navigation-bar-react a.icon-link-generic-react')
        for link in old_links:
            href = await link.get_attribute('href')
            span = await link.query_selector('span.icon-link-generic-react__text')
            text = await span.inner_text() if span else ''
            # Only include video links (skip PDF links)
            if href and 'videoarkiv' in href:
                video_links.append({
                    'url': f"https://www.stortinget.no{href}" if not href.startswith('http') else href,
                    'type': text,
                    'source_page': url,
                    'format': 'old'
                })
    
    return video_links

async def process_url(page, url: str, pbar) -> List[Dict]:
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # Wait for either selector with a more generous timeout
        try:
            await page.wait_for_selector('ul.icon-link-list, div.minutes-navigation-bar-react', timeout=20000)
        except Exception as e:
            tqdm.write(f"Warning: Neither selector found for {url}")
            pbar.update(1)
            return []
        
        # Add a small delay to ensure content is loaded
        await page.wait_for_timeout(1000)
        
        video_links = await extract_video_links(page, url)
        format_type = 'old' if video_links and video_links[0]['format'] == 'old' else 'new'
        tqdm.write(f"Found {len(video_links)} video links (Format: {format_type}) for {url}")
        pbar.update(1)
        return video_links
        
    except Exception as e:
        tqdm.write(f"Error processing {url}: {str(e)}")
        pbar.update(1)
        return []

def get_all_urls(csv_path: str) -> List[str]:
    # Read all URLs from the CSV file
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row['link'] for row in reader]

def save_progress(video_links: List[Dict], current_count: int):
    """Save the current progress to CSV"""
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'video_links.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'type', 'source_page', 'format'])
        writer.writeheader()
        writer.writerows(video_links)
    
    tqdm.write(f"\nProgress saved after processing {current_count} transcripts")

async def process_batch(context, urls: List[str], start_idx: int, batch_size: int, pbar) -> List[Dict]:
    pages = []
    results = []
    
    try:
        # Create pages for this batch
        pages = await asyncio.gather(*[context.new_page() for _ in range(batch_size)])
        
        # Process URLs in this batch
        tasks = []
        for i, page in enumerate(pages):
            url_idx = start_idx + i
            if url_idx < len(urls):
                tasks.append(process_url(page, urls[url_idx], pbar))
        
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            for result in batch_results:
                results.extend(result)
        
    finally:
        # Close all pages in this batch
        await asyncio.gather(*[page.close() for page in pages])
    
    return results

async def main():
    # Get all URLs from the transcript links CSV
    transcript_csv_path = 'transcript_links_with_dates.csv'
    if not Path(transcript_csv_path).exists():
        print(f"Error: {transcript_csv_path} not found!")
        return
    
    all_urls = get_all_urls(transcript_csv_path)
    total_urls = len(all_urls)
    print(f"\nFound {total_urls} transcripts to process")
    
    async with async_playwright() as p:
        # Launch browser in stealth mode
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            viewport={'width': 1280, 'height': 720}
        )
        
        # Add stealth mode configurations
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
        
        print("\nStarting processing with async batches...")
        start_time = time.time()
        
        # Process URLs in batches
        batch_size = 5  # Number of concurrent pages
        all_video_links = []
        
        with tqdm(total=total_urls, desc="Total Progress") as pbar:
            for start_idx in range(0, len(all_urls), batch_size):
                batch_results = await process_batch(
                    context,
                    all_urls,
                    start_idx,
                    batch_size,
                    pbar
                )
                all_video_links.extend(batch_results)
                
                # Save progress after each batch
                save_progress(all_video_links, min(start_idx + batch_size, total_urls))
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nProcessing complete!")
        print(f"Total video links found: {len(all_video_links)}")
        print(f"Total processing time: {duration:.2f} seconds")
        print(f"Average time per transcript: {duration/total_urls:.2f} seconds")
        print(f"Results saved to: output/video_links.csv")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
