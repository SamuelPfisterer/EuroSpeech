#!/usr/bin/env python3
import os
import csv
import time
import random
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from markdownify import markdownify as md
from tqdm import tqdm

# Create directories if they don't exist
def ensure_dirs():
    Path("transcripts/html").mkdir(parents=True, exist_ok=True)
    Path("transcripts/markdown").mkdir(parents=True, exist_ok=True)

# Process a single URL using a browser context
async def process_url(browser, row, semaphore):
    async with semaphore:  # Limit concurrent tab count
        video_id = row['video_id']
        url = row['processed_transcript_text_link']
        
        html_file = f"transcripts/html/{video_id}.html"
        md_file = f"transcripts/markdown/{video_id}.md"
        
        # Skip if both files already exist
        if os.path.exists(html_file) and os.path.exists(md_file):
            return True
        
        try:
            # Create a new context for each URL (like a new browser session)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
            )
            
            # Create a new page in this context
            page = await context.new_page()
            
            # Set timeout to 60 seconds
            page.set_default_timeout(60000)
            
            # Random delay to prevent detection
            await asyncio.sleep(random.uniform(0.5, 2))
            
            # Navigate to the URL
            await page.goto(url)
            
            # Random scrolling to appear more human-like
            for _ in range(random.randint(2, 4)):
                await page.mouse.wheel(0, random.randint(100, 300))
                await asyncio.sleep(random.uniform(0.3, 1.0))
            
            # Wait for content to load
            await page.wait_for_selector("body")
            
            # Get HTML content
            html_content = await page.content()
            
            # Save HTML content
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Convert to markdown and save
            markdown_content = md(html_content)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # Close the context when done
            await context.close()
            
            return True
        except Exception as e:
            print(f"Error processing {video_id}: {str(e)}")
            return False

async def main_async():
    # Create necessary directories
    ensure_dirs()
    
    # Read the CSV file
    with open("sweden_links.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Found {len(rows)} links to process")
    
    # Count existing files to update progress bar
    processed_count = 0
    for row in rows:
        video_id = row['video_id']
        html_file = f"transcripts/html/{video_id}.html"
        md_file = f"transcripts/markdown/{video_id}.md"
        if os.path.exists(html_file) and os.path.exists(md_file):
            processed_count += 1
    
    print(f"Already processed: {processed_count}/{len(rows)}")
    
    # Maximum number of concurrent tabs
    max_concurrent = 6
    
    # Create a semaphore to limit the number of concurrent tabs
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async with async_playwright() as p:
        # Launch a single browser instance in headless mode
        browser = await p.chromium.launch(headless=True)
        
        # Create tasks for all URLs
        tasks = []
        pbar = tqdm(total=len(rows), desc="Processing URLs", initial=processed_count)
        
        for row in rows:
            video_id = row['video_id']
            html_file = f"transcripts/html/{video_id}.html"
            md_file = f"transcripts/markdown/{video_id}.md"
            
            # Skip if already processed
            if os.path.exists(html_file) and os.path.exists(md_file):
                continue
            
            # Create and store the task
            task = asyncio.create_task(process_url(browser, row, semaphore))
            
            # Add a callback to update the progress bar
            task.add_done_callback(lambda _: pbar.update(1))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close the progress bar
        pbar.close()
        
        # Close the browser
        await browser.close()
    
    # Count successes
    success_count = sum(1 for r in results if r is True)
    print(f"Processing complete. Successfully processed {success_count} new URLs.")
    print(f"Total processed: {processed_count + success_count}/{len(rows)}")

def main():
    # Run the async main function
    asyncio.run(main_async())

if __name__ == "__main__":
    main() 