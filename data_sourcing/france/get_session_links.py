from playwright.async_api import async_playwright
import asyncio
import time
import random
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import math

async def random_delay(min_seconds=2, max_seconds=5):
    """Add random delay between requests to mimic human behavior"""
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))

async def setup_stealth_browser(playwright):
    """Setup browser with stealth configurations"""
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        java_script_enabled=True,
        bypass_csp=True,
        extra_http_headers={
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    )
    return browser, context

async def extract_session_info(element):
    """Extract session information from a div element"""
    try:
        # Get the link element with class "vr"
        link = await element.query_selector('a.vr')
        if not link:
            return None

        href = await link.get_attribute('href')
        data_title = await link.get_attribute('data-title')
        
        # Extract date information
        date_span = await link.query_selector('span.date')
        if date_span:
            day = await (await date_span.query_selector('span.jour')).inner_text()
            month = await (await date_span.query_selector('span.mois')).inner_text()
            year = await (await date_span.query_selector('span.annee')).inner_text()
            full_date = f"{day} {month} {year}"
        
        # Get title
        title_span = await link.query_selector('span.titre')
        title = await title_span.inner_text() if title_span else ""

        return {
            'date': full_date,
            'title': title,
            'link': f"https://videos.assemblee-nationale.fr/{href}",
            'raw_data_title': data_title
        }
    except Exception as e:
        print(f"Error extracting session info: {e}")
        return None

def save_results(sessions: List[Dict], output_file: Path):
    """Save the scraped data to a CSV file"""
    # Define whether we need to write headers (only for new files)
    write_headers = not output_file.exists()
    
    # Open in append mode with UTF-8 encoding
    with open(output_file, mode='a', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['date', 'title', 'link', 'raw_data_title']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write headers only for new files
        if write_headers:
            writer.writeheader()
        
        # Write all sessions
        for session in sessions:
            writer.writerow(session)

async def process_page(page, url: str, output_file: Path) -> None:
    """Process a single page"""
    try:
        print(f"Starting to process: {url}")
        await page.goto(url)
        await random_delay(1, 3)  # Shorter delays for concurrent processing
        
        # Wait for the content to load
        await page.wait_for_selector('#myCarousel-contenu')
        
        # Extract all session divs
        session_elements = await page.query_selector_all('.span4')
        
        # Process sessions for this page
        page_sessions = []
        for element in session_elements:
            session_info = await extract_session_info(element)
            if session_info:
                page_sessions.append(session_info)
        
        # Save progress for this page
        if page_sessions:
            save_results(page_sessions, output_file)
            print(f"Saved {len(page_sessions)} sessions from URL: {url}")
        
    except Exception as e:
        print(f"Error processing URL {url}: {e}")

async def process_page_batch(context, urls: List[str], output_file: Path) -> None:
    """Process a batch of pages concurrently"""
    # Create a page for each URL
    pages = await asyncio.gather(*(context.new_page() for _ in urls))
    
    # Process all pages concurrently
    await asyncio.gather(*(process_page(page, url, output_file) 
                         for page, url in zip(pages, urls)))
    
    # Close all pages
    await asyncio.gather(*(page.close() for page in pages))

async def scrape_sessions():
    """Main function to scrape session data"""
    async with async_playwright() as playwright:
        browser, context = await setup_stealth_browser(playwright)
        
        # Create output file at the start
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'sessions_{timestamp}.csv'
        
        base_url = "https://videos.assemblee-nationale.fr/seance-publique.p"
        total_pages = 545  # Full number of pages
        batch_size = 10  # Increased batch size for full run
        
        # Process pages in batches
        for batch_start in range(1, total_pages + 1, batch_size):
            batch_end = min(batch_start + batch_size, total_pages + 1)
            urls = [f"{base_url}{page_num}" for page_num in range(batch_start, batch_end)]
            
            print(f"\nProcessing batch {batch_start}-{batch_end-1} of {total_pages}")
            await process_page_batch(context, urls, output_file)
            
            # Add a small delay between batches to avoid overwhelming the server
            await random_delay(2, 4)
        
        await browser.close()
        print(f"\nScraping completed. Results saved to: {output_file}")

def main():
    """Entry point with asyncio handling"""
    asyncio.run(scrape_sessions())

if __name__ == "__main__":
    main()
