from playwright.sync_api import sync_playwright
import pandas as pd
import time
import logging
from typing import Optional, List
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class VideoStreamScraper:
    def __init__(self, max_wait_time: int = 5):
        self.max_wait_time = max_wait_time
    
    def capture_video_stream(self, url: str) -> Optional[str]:
        """Capture video stream URL for a given page URL."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            final_url = None
            start_time = time.time()
            
            def handle_request(request):
                nonlocal final_url
                if final_url:  # Skip if we already found our URL
                    return
                    
                url = request.url
                # Look specifically for the main playlist m3u8
                if 'playlist.m3u8' in url.lower() and 'senato-vod' in url.lower():
                    final_url = url
                    elapsed = time.time() - start_time
                    logging.info(f"[{elapsed:.2f}s] Found streaming URL: {url}")
                    
            # Monitor all requests
            page.on('request', handle_request)
            
            try:
                logging.info(f"Processing URL: {url}")
                page.goto(url)
                
                # Simple wait for the URL to be captured
                while not final_url and (time.time() - start_time) < self.max_wait_time:
                    page.wait_for_timeout(100)  # Quick check every 100ms
                
                if not final_url:
                    logging.warning(f"No streaming URL found for: {url}")
                
            except Exception as e:
                logging.error(f"Error processing {url}: {str(e)}")
            
            finally:
                browser.close()
            
            return final_url

def process_video_links(input_csv: str = 'getting_links/italian_senate_meetings_ready_to_download.csv', 
                       output_csv: str = 'streaming_urls.csv'):
    """Process all video links from input CSV and save results to output CSV."""
    scraper = VideoStreamScraper()
    
    try:
        # Read input CSV
        df = pd.read_csv(input_csv)
        
        if 'generic_video_link' not in df.columns:
            raise ValueError("CSV must contain a 'generic_video_link' column")
        
        results = []
        total = len(df)
        start_time = time.time()
        
        # Process each URL
        for idx, row in df.iterrows():
            current_time = time.time()
            elapsed = current_time - start_time
            avg_time_per_url = elapsed / (idx + 1) if idx > 0 else 0
            remaining_urls = total - (idx + 1)
            estimated_time_remaining = avg_time_per_url * remaining_urls
            
            logging.info(f"\nProcessing URL {idx + 1}/{total}")
            logging.info(f"Elapsed time: {elapsed:.2f}s")
            logging.info(f"Estimated time remaining: {estimated_time_remaining:.2f}s")
            
            video_url = scraper.capture_video_stream(row['generic_video_link'])
            
            results.append({
                'video_id': row['video_id'],
                'date': row['date'],
                'legislation': row['legislation'],
                'sitting_number': row['sitting_number'],
                'original_url': row['generic_video_link'],
                'streaming_url': video_url
            })
            
            # Save intermediate results every 10 items
            if (idx + 1) % 10 == 0:
                pd.DataFrame(results).to_csv(output_csv, index=False)
                logging.info(f"Saved intermediate results to {output_csv}")
        
        # Save final results
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_csv, index=False)
        
        # Print summary
        successful = results_df['streaming_url'].notna().sum()
        total_time = time.time() - start_time
        logging.info(f"\nSummary:")
        logging.info(f"Successfully processed {successful}/{total} video links")
        logging.info(f"Total time: {total_time:.2f}s")
        logging.info(f"Average time per URL: {total_time/total:.2f}s")
        logging.info(f"Results saved to {output_csv}")
        
    except Exception as e:
        logging.error(f"Error processing CSV: {str(e)}")
        raise

if __name__ == "__main__":
    # Process all video links
    process_video_links()