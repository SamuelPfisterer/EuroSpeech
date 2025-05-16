from playwright.async_api import async_playwright
import pandas as pd
import time
import logging
import asyncio
from typing import Optional, List, Dict
import os
import random
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AsyncVideoScraper:
    def __init__(self, max_wait_time: int = 8, max_parallel: int = 1):
        self.max_wait_time = max_wait_time
        self.max_parallel = max_parallel
        self.semaphore = asyncio.Semaphore(max_parallel)
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()

    @retry(
        stop=stop_after_attempt(3),  # Try 3 times
        wait=wait_exponential(multiplier=1, min=4, max=10),  # Wait 4-10 seconds between retries
        reraise=True
    )
    async def capture_video_stream(self, row_data: Dict, retry_state=None) -> Dict:
        """Capture video stream URL for a given page URL with retry logic."""
        async with self.semaphore:
            # Random delay between 3 and 6 seconds
            delay = random.uniform(3, 6)
            await asyncio.sleep(delay)
            
            context = await self.browser.new_context()
            page = await context.new_page()
            
            final_url = None
            start_time = time.time()
            
            async def handle_request(request):
                nonlocal final_url
                if final_url:  # Skip if we already found our URL
                    return
                    
                url = request.url
                # Look specifically for the main playlist m3u8
                if 'playlist.m3u8' in url.lower() and 'senato-vod' in url.lower():
                    final_url = url
                    elapsed = time.time() - start_time
                    logging.info(f"[{elapsed:.2f}s] Found streaming URL for video {row_data['video_id']}")
            
            # Monitor all requests
            page.on('request', handle_request)
            
            try:
                url = row_data['generic_video_link']
                attempt_number = retry_state.attempt_number if retry_state else 1
                logging.info(f"Processing video {row_data['video_id']} (attempt {attempt_number})")
                
                # Navigate to the page
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                
                # Wait for the streaming URL or timeout
                wait_start = time.time()
                while not final_url and (time.time() - wait_start) < self.max_wait_time:
                    await asyncio.sleep(0.1)  # Quick check every 100ms
                    
                if not final_url:
                    logging.warning(f"No streaming URL found for video {row_data['video_id']}")
                    raise Exception("Failed to find streaming URL")  # Trigger retry
                
            except Exception as e:
                logging.error(f"Error processing video {row_data['video_id']}: {str(e)}")
                raise  # Re-raise for retry logic
            
            finally:
                await context.close()
                # Add an additional random delay after closing the context
                await asyncio.sleep(random.uniform(1, 2))
            
            # Create result with all original columns plus streaming_url
            result = {
                'video_id': row_data['video_id'],
                'generic_video_link': row_data['generic_video_link'],
                'html_link': row_data['html_link'],
                'pdf_link': row_data['pdf_link'],
                'date': row_data['date'],
                'legislation': row_data['legislation'],
                'sitting_number': row_data['sitting_number'],
                'streaming_url': final_url
            }
            return result

async def process_batch(scraper: AsyncVideoScraper, rows: List[Dict]) -> List[Dict]:
    """Process a batch of rows concurrently."""
    completed = 0
    total = len(rows)
    start_time = time.time()
    results = []

    # Create tasks for all rows
    tasks = [scraper.capture_video_stream(row) for row in rows]
    
    # Process tasks as they complete
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            results.append(result)
            
            # Update progress
            completed += 1
            current_time = time.time()
            elapsed = current_time - start_time
            avg_time_per_url = elapsed / completed
            remaining_urls = total - completed
            estimated_time_remaining = avg_time_per_url * remaining_urls
            
            # Log progress
            logging.info(f"\nProcessed {completed}/{total}")
            logging.info(f"Elapsed time: {elapsed:.2f}s")
            logging.info(f"Estimated time remaining: {estimated_time_remaining:.2f}s")
            
            # Save intermediate results every 5 items
            if completed % 5 == 0:
                pd.DataFrame(results).to_csv('streaming_urls.csv', index=False)
                logging.info(f"Saved intermediate results to streaming_urls.csv")
                
        except Exception as e:
            logging.error(f"Failed to process task: {str(e)}")
            # Add failed result to maintain order
            results.append({
                'video_id': rows[completed]['video_id'],
                'generic_video_link': rows[completed]['generic_video_link'],
                'html_link': rows[completed]['html_link'],
                'pdf_link': rows[completed]['pdf_link'],
                'date': rows[completed]['date'],
                'legislation': rows[completed]['legislation'],
                'sitting_number': rows[completed]['sitting_number'],
                'streaming_url': None
            })
    
    return results

async def process_video_links_async(
    input_csv: str = 'getting_links/italian_senate_meetings_ready_to_download.csv',
    output_csv: str = 'streaming_urls.csv',
    max_parallel: int = 1
):
    """Process all video links using async Playwright and save results to output CSV."""
    try:
        # Read input CSV
        df = pd.read_csv(input_csv)
        
        if 'generic_video_link' not in df.columns:
            raise ValueError("CSV must contain a 'generic_video_link' column")
        
        total = len(df)
        start_time = time.time()
        logging.info(f"Starting to process {total} videos with {max_parallel} parallel tabs")
        
        # Convert DataFrame rows to list of dicts
        rows = df.to_dict('records')
        
        async with AsyncVideoScraper(max_parallel=max_parallel) as scraper:
            # Process all rows
            results = await process_batch(scraper, rows)
            
            # Save final results
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_csv, index=False)
            
            # Print summary
            successful = results_df['streaming_url'].notna().sum()
            total_time = time.time() - start_time
            logging.info(f"\nFinal Summary:")
            logging.info(f"Successfully processed {successful}/{total} video links")
            logging.info(f"Total time: {total_time:.2f}s")
            logging.info(f"Average time per URL: {total_time/total:.2f}s")
            logging.info(f"Results saved to {output_csv}")
            
            # Print success rate
            success_rate = (successful / total) * 100
            logging.info(f"Success rate: {success_rate:.1f}%")
            
    except Exception as e:
        logging.error(f"Error processing CSV: {str(e)}")
        raise

def main():
    # Use single tab with longer delays
    asyncio.run(process_video_links_async(max_parallel=1))

if __name__ == "__main__":
    main() 