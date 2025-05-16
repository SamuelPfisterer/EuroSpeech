import pandas as pd
import requests
import re
import logging
import random
from typing import Tuple, List
from playwright.sync_api import sync_playwright
import time
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_video_link_requests(url: str) -> Tuple[str, str]:
    """
    First, try following redirects on the original URL
    """
    try:
        # First, try following redirects on the original URL
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        # If the final URL is different and ends with .mp4, use it
        if response.url != url and response.url.endswith('.mp4'):
            logging.info(f"Found MP4 by following redirects: {response.url}")
            return response.url, 'mp4_video_link'
        
        # If the final URL is different, do a GET to confirm it's a video
        if response.url != url:
            get_response = requests.get(response.url, stream=True, timeout=10)
            content_type = get_response.headers.get('Content-Type', '')
            if 'video' in content_type or 'mp4' in content_type:
                logging.info(f"Confirmed video link through redirects: {response.url}")
                return response.url, 'mp4_video_link'
    except Exception as e:
        logging.warning(f"Error following redirects for {url}: {str(e)}")
    
    # Rest of the existing extraction methods...
    logging.info(f"Extracting downloadable link using requests from: {url}")
    
    # Check if the URL is already a direct media URL
    if 'cdn.tiesraides.lv' in url:
        # If it's already an MP4, return it directly
        if url.endswith('.mp4'):
            return url, 'mp4_video_link'
        
        # Try appending .mp4 and follow redirects - this is the most common pattern
        mp4_url = f"{url}.mp4"
        try:
            # Use allow_redirects=True to follow any redirects
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                # If we were redirected, use the final URL
                final_url = response.url
                content_type = response.headers.get('Content-Type', '')
                if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                    logging.info(f"Found MP4 by appending .mp4 and following redirects: {final_url}")
                    return final_url, 'mp4_video_link'
                else:
                    logging.info(f"Found URL by appending .mp4, but content type is {content_type}: {final_url}")
                    # Try a GET request to see if it's actually a video
                    try:
                        get_response = requests.get(final_url, timeout=10, stream=True)
                        # Read just the first few bytes to check content type
                        get_response.raw.read(1024)
                        content_type = get_response.headers.get('Content-Type', '')
                        if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                            logging.info(f"Confirmed MP4 content type with GET request: {final_url}")
                            return final_url, 'mp4_video_link'
                    except Exception as e:
                        logging.warning(f"Error checking content with GET: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL with redirects: {str(e)}")
        
        # Try different MP4 patterns if the simple append didn't work
        mp4_patterns = [
            f"{url}/video.mp4",
            f"{url}/download.mp4",
            f"{url}/media.mp4"
        ]
        
        for mp4_url in mp4_patterns:
            try:
                # Check if the MP4 URL exists
                response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    final_url = response.url
                    content_type = response.headers.get('Content-Type', '')
                    if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                        logging.info(f"Found MP4: {final_url}")
                        return final_url, 'mp4_video_link'
            except Exception as e:
                logging.warning(f"Failed to check MP4 URL {mp4_url}: {str(e)}")
        
        # If we can't find an MP4, use the original URL with generic_video_link
        logging.info(f"No MP4 found, using generic_video_link for: {url}")
        return url, 'generic_video_link'
    
    # If it's a webpage, try to extract the video URL
    try:
        response = requests.get(url, timeout=10)
        
        # Look for mp4 links
        mp4_link = re.search(r'(https?://[^"\']+\.mp4)', response.text)
        if mp4_link:
            mp4_url = mp4_link.group(1)
            logging.info(f"Found MP4 link in page: {mp4_url}")
            return mp4_url, 'mp4_video_link'
        
        # Look for iframe sources that might contain videos
        iframe_src = re.search(r'<iframe[^>]+src=["\'](https?://[^\'"]+)["\']', response.text)
        if iframe_src:
            iframe_url = iframe_src.group(1)
            # Recursively process the iframe URL
            return process_video_link_requests(iframe_url)
        
        # Try appending .mp4 to the original URL
        mp4_url = f"{url}.mp4"
        try:
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                logging.info(f"Found MP4 by appending .mp4 to URL: {final_url}")
                return final_url, 'mp4_video_link'
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL: {str(e)}")
    
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
    
    # If we can't determine the type, use generic video handler
    logging.info(f"Using generic_video_link handler as fallback for: {url}")
    return url, 'generic_video_link'

def process_video_link_playwright(url: str) -> Tuple[str, str]:
    """
    First, try following redirects on the original URL
    """
    try:
        # Use requests to follow redirects first
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        # If the final URL is different and ends with .mp4, use it
        if response.url != url and response.url.endswith('.mp4'):
            logging.info(f"Found MP4 by following redirects: {response.url}")
            return response.url, 'mp4_video_link'
        
        # If the final URL is different, do a GET to confirm it's a video
        if response.url != url:
            get_response = requests.get(response.url, stream=True, timeout=10)
            content_type = get_response.headers.get('Content-Type', '')
            if 'video' in content_type or 'mp4' in content_type:
                logging.info(f"Confirmed video link through redirects: {response.url}")
                return response.url, 'mp4_video_link'
    except Exception as e:
        logging.warning(f"Error following redirects for {url}: {str(e)}")
    
    # Rest of the existing extraction methods...
    logging.info(f"Extracting downloadable link using Playwright from: {url}")
    
    # Check if the URL is already a direct media URL
    if 'cdn.tiesraides.lv' in url:
        # If it's already an MP4, return it directly
        if url.endswith('.mp4'):
            return url, 'mp4_video_link'
        
        # Try appending .mp4 and follow redirects - this is the most common pattern
        mp4_url = f"{url}.mp4"
        try:
            # Use allow_redirects=True to follow any redirects
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                # If we were redirected, use the final URL
                final_url = response.url
                content_type = response.headers.get('Content-Type', '')
                if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                    logging.info(f"Found MP4 by appending .mp4 and following redirects: {final_url}")
                    return final_url, 'mp4_video_link'
                else:
                    logging.info(f"Found URL by appending .mp4, but content type is {content_type}: {final_url}")
                    # Try a GET request to see if it's actually a video
                    try:
                        get_response = requests.get(final_url, timeout=10, stream=True)
                        # Read just the first few bytes to check content type
                        get_response.raw.read(1024)
                        content_type = get_response.headers.get('Content-Type', '')
                        if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                            logging.info(f"Confirmed MP4 content type with GET request: {final_url}")
                            return final_url, 'mp4_video_link'
                    except Exception as e:
                        logging.warning(f"Error checking content with GET: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL with redirects: {str(e)}")
        
        # Try different MP4 patterns if the simple append didn't work
        mp4_patterns = [
            f"{url}/video.mp4",
            f"{url}/download.mp4",
            f"{url}/media.mp4"
        ]
        
        for mp4_url in mp4_patterns:
            try:
                # Check if the MP4 URL exists
                response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    final_url = response.url
                    content_type = response.headers.get('Content-Type', '')
                    if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                        logging.info(f"Found MP4: {final_url}")
                        return final_url, 'mp4_video_link'
            except Exception as e:
                logging.warning(f"Failed to check MP4 URL {mp4_url}: {str(e)}")
    
    # Use Playwright to load the page and check for video elements
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Navigate to the URL
            page.goto(url, timeout=30000)
            
            # Wait for potential video elements to load
            page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check for video elements
            video_elements = page.query_selector_all('video')
            for video in video_elements:
                src = video.get_attribute('src')
                if src and '.mp4' in src:
                    # Make sure it's a full URL
                    if src.startswith('http'):
                        mp4_url = src
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{src if src.startswith('/') else '/' + src}"
                    
                    logging.info(f"Found MP4 in video element: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Check for source elements within video tags
            source_elements = page.query_selector_all('video source')
            for source in source_elements:
                src = source.get_attribute('src')
                if src and '.mp4' in src:
                    # Make sure it's a full URL
                    if src.startswith('http'):
                        mp4_url = src
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{src if src.startswith('/') else '/' + src}"
                    
                    logging.info(f"Found MP4 in source element: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Check for iframe elements
            iframe_elements = page.query_selector_all('iframe')
            for iframe in iframe_elements:
                iframe_src = iframe.get_attribute('src')
                if iframe_src:
                    logging.info(f"Found iframe with src: {iframe_src}")
                    # We could recursively process this iframe, but for simplicity
                    # we'll just note it for now
            
            # Check network requests for MP4 files
            page.reload()
            page.wait_for_load_state('networkidle', timeout=10000)
            
            # Execute JavaScript to find video URLs in the page
            js_result = page.evaluate('''() => {
                const videoUrls = [];
                // Check for video elements
                document.querySelectorAll('video').forEach(video => {
                    if (video.src) videoUrls.push(video.src);
                });
                
                // Check for source elements
                document.querySelectorAll('source').forEach(source => {
                    if (source.src) videoUrls.push(source.src);
                });
                
                // Check for object/embed elements
                document.querySelectorAll('object, embed').forEach(obj => {
                    if (obj.data) videoUrls.push(obj.data);
                });
                
                // Look for MP4 URLs in all attributes
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    for (const attr of el.attributes) {
                        if (attr.value && attr.value.includes('.mp4')) {
                            videoUrls.push(attr.value);
                        }
                    }
                }
                
                return videoUrls;
            }''')
            
            for video_url in js_result:
                if '.mp4' in video_url:
                    # Make sure it's a full URL
                    if video_url.startswith('http'):
                        mp4_url = video_url
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{video_url if video_url.startswith('/') else '/' + video_url}"
                    
                    logging.info(f"Found MP4 via JavaScript: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Get the page content and look for MP4 links
            content = page.content()
            mp4_links = re.findall(r'(https?://[^"\']+\.mp4)', content)
            if mp4_links:
                mp4_url = mp4_links[0]
                logging.info(f"Found MP4 link in page content: {mp4_url}")
                browser.close()
                return mp4_url, 'mp4_video_link'
            
            # Try to find onclick handlers that might contain video URLs
            onclick_elements = page.query_selector_all('[onclick]')
            for element in onclick_elements:
                onclick = element.get_attribute('onclick')
                if onclick and ('window.open' in onclick or '.mp4' in onclick):
                    # Extract URL from onclick
                    onclick_url_match = re.search(r"window\.open\('([^']+)'", onclick)
                    if onclick_url_match:
                        onclick_url = onclick_url_match.group(1)
                        logging.info(f"Found URL in onclick: {onclick_url}")
                        
                        # If it's an MP4 URL, return it
                        if '.mp4' in onclick_url:
                            browser.close()
                            return onclick_url, 'mp4_video_link'
                        
                        # Try appending .mp4 to the onclick URL
                        mp4_url = f"{onclick_url}.mp4"
                        try:
                            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                final_url = response.url
                                logging.info(f"Found MP4 by appending .mp4 to onclick URL: {final_url}")
                                browser.close()
                                return final_url, 'mp4_video_link'
                        except Exception as e:
                            logging.warning(f"Failed to check appended MP4 URL from onclick: {str(e)}")
            
        except Exception as e:
            logging.error(f"Error with Playwright for {url}: {str(e)}")
        
        browser.close()
    
    # If we can't determine the type, use generic video handler
    logging.info(f"Using generic_video_link handler as fallback for: {url}")
    return url, 'generic_video_link'

def test_video_extraction(csv_file: str, num_samples: int = 5) -> None:
    """
    Test video extraction on a sample of videos from the CSV file.
    
    Args:
        csv_file: Path to the CSV file with video links
        num_samples: Number of random samples to test
    """
    # Load the CSV file
    df = pd.read_csv(csv_file)
    
    # Ensure we have a column with video links
    video_link_col = None
    for col in ['processed_video_link', 'video_url', 'URL']:
        if col in df.columns:
            video_link_col = col
            break
    
    if not video_link_col:
        logging.error("Could not find a column with video links in the CSV file")
        return
    
    # Get random samples
    if len(df) <= num_samples:
        samples = df
    else:
        samples = df.sample(num_samples)
    
    # Test both methods on each sample
    results = []
    
    for idx, row in samples.iterrows():
        video_url = row[video_link_col]
        
        logging.info(f"\n{'='*80}\nTesting URL: {video_url}\n{'='*80}")
        
        # Test requests method
        try:
            start_time = time.time()
            requests_result, requests_type = process_video_link_requests(video_url)
            requests_time = time.time() - start_time
            logging.info(f"Requests method result: {requests_result} (type: {requests_type})")
            logging.info(f"Requests method took {requests_time:.2f} seconds")
        except Exception as e:
            logging.error(f"Error with requests method: {str(e)}")
            requests_result = "ERROR"
            requests_type = "ERROR"
            requests_time = 0
        
        # Test Playwright method
        try:
            start_time = time.time()
            playwright_result, playwright_type = process_video_link_playwright(video_url)
            playwright_time = time.time() - start_time
            logging.info(f"Playwright method result: {playwright_result} (type: {playwright_type})")
            logging.info(f"Playwright method took {playwright_time:.2f} seconds")
        except Exception as e:
            logging.error(f"Error with Playwright method: {str(e)}")
            playwright_result = "ERROR"
            playwright_type = "ERROR"
            playwright_time = 0
        
        # Store results
        results.append({
            'original_url': video_url,
            'requests_result': requests_result,
            'requests_type': requests_type,
            'requests_time': requests_time,
            'playwright_result': playwright_result,
            'playwright_type': playwright_type,
            'playwright_time': playwright_time,
            'success': requests_result != video_url or playwright_result != video_url
        })
    
    # Save results to CSV
    results_df = pd.DataFrame(results)
    results_file = 'video_extraction_test_results.csv'
    results_df.to_csv(results_file, index=False)
    logging.info(f"Saved test results to {results_file}")
    
    # Print summary
    success_count = sum(results_df['success'])
    logging.info(f"\nSummary: Successfully extracted MP4 links for {success_count}/{len(results_df)} videos")
    
    if success_count > 0:
        logging.info("Successful extractions:")
        for idx, row in results_df[results_df['success']].iterrows():
            if row['requests_result'] != row['original_url']:
                logging.info(f"  Requests: {row['original_url']} -> {row['requests_result']}")
            if row['playwright_result'] != row['original_url']:
                logging.info(f"  Playwright: {row['original_url']} -> {row['playwright_result']}")

def create_video_link_extractor(csv_file: str) -> None:
    """
    Create a video_link_extractors.py file based on test results.
    
    Args:
        csv_file: Path to the CSV file with test results
    """
    # Load test results
    results_df = pd.read_csv(csv_file)
    
    # Determine which method worked better
    requests_success = sum(results_df['requests_result'] != results_df['original_url'])
    playwright_success = sum(results_df['playwright_result'] != results_df['original_url'])
    
    # Create the extractor file
    with open('video_link_extractors.py', 'w') as f:
        f.write("""from typing import Tuple
import requests
import re
import logging
""")

        # If Playwright was more successful, include it
        if playwright_success >= requests_success:
            f.write("""from playwright.sync_api import sync_playwright
""")

        f.write("""
def process_video_link(url: str) -> Tuple[str, str]:
    \"\"\"
    Extract downloadable video link from Latvia parliament URL.
    
    Args:
        url: The URL to the video page or stream
        
    Returns:
        Tuple containing (video_url, link_type)
    \"\"\"
    logging.info(f"Extracting downloadable link from: {url}")
    
""")

        # Include the better method based on test results
        if playwright_success > requests_success:
            f.write("""    # Use Playwright method which had better results in testing
    return process_video_link_playwright(url)
""")
        else:
            f.write("""    # Use Requests method which had better results in testing
    return process_video_link_requests(url)
""")

        # Include both methods for reference
        f.write("""
def process_video_link_requests(url: str) -> Tuple[str, str]:
    \"\"\"
    Extract MP4 video link from Latvia parliament URL using requests.
    \"\"\"
    # Check if the URL is already a direct media URL
    if 'cdn.tiesraides.lv' in url:
        # If it's already an MP4, return it directly
        if url.endswith('.mp4'):
            return url, 'mp4_video_link'
        
        # Try appending .mp4 and follow redirects - this is the most common pattern
        mp4_url = f"{url}.mp4"
        try:
            # Use allow_redirects=True to follow any redirects
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                # If we were redirected, use the final URL
                final_url = response.url
                content_type = response.headers.get('Content-Type', '')
                if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                    logging.info(f"Found MP4 by appending .mp4 and following redirects: {final_url}")
                    return final_url, 'mp4_video_link'
                else:
                    logging.info(f"Found URL by appending .mp4, but content type is {content_type}: {final_url}")
                    # Try a GET request to see if it's actually a video
                    try:
                        get_response = requests.get(final_url, timeout=10, stream=True)
                        # Read just the first few bytes to check content type
                        get_response.raw.read(1024)
                        content_type = get_response.headers.get('Content-Type', '')
                        if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                            logging.info(f"Confirmed MP4 content type with GET request: {final_url}")
                            return final_url, 'mp4_video_link'
                    except Exception as e:
                        logging.warning(f"Error checking content with GET: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL with redirects: {str(e)}")
        
        # Try different MP4 patterns if the simple append didn't work
        mp4_patterns = [
            f"{url}/video.mp4",
            f"{url}/download.mp4",
            f"{url}/media.mp4"
        ]
        
        for mp4_url in mp4_patterns:
            try:
                # Check if the MP4 URL exists
                response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    final_url = response.url
                    content_type = response.headers.get('Content-Type', '')
                    if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                        logging.info(f"Found MP4: {final_url}")
                        return final_url, 'mp4_video_link'
            except Exception as e:
                logging.warning(f"Failed to check MP4 URL {mp4_url}: {str(e)}")
        
        # If we can't find an MP4, use the original URL with generic_video_link
        logging.info(f"No MP4 found, using generic_video_link for: {url}")
        return url, 'generic_video_link'
    
    # If it's a webpage, try to extract the video URL
    try:
        response = requests.get(url, timeout=10)
        
        # Look for mp4 links
        mp4_link = re.search(r'(https?://[^"\']+\.mp4)', response.text)
        if mp4_link:
            mp4_url = mp4_link.group(1)
            logging.info(f"Found MP4 link in page: {mp4_url}")
            return mp4_url, 'mp4_video_link'
        
        # Look for iframe sources that might contain videos
        iframe_src = re.search(r'<iframe[^>]+src=["\'](https?://[^\'"]+)["\']', response.text)
        if iframe_src:
            iframe_url = iframe_src.group(1)
            # Recursively process the iframe URL
            return process_video_link_requests(iframe_url)
        
        # Try appending .mp4 to the original URL
        mp4_url = f"{url}.mp4"
        try:
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                logging.info(f"Found MP4 by appending .mp4 to URL: {final_url}")
                return final_url, 'mp4_video_link'
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL: {str(e)}")
    
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
    
    # If we can't determine the type, use generic video handler
    logging.info(f"Using generic_video_link handler as fallback for: {url}")
    return url, 'generic_video_link'
""")

        # Include Playwright method if it was successful
        if playwright_success > 0:
            f.write("""
def process_video_link_playwright(url: str) -> Tuple[str, str]:
    \"\"\"
    Extract MP4 video link from Latvia parliament URL using Playwright.
    \"\"\"
    # Check if the URL is already a direct media URL
    if 'cdn.tiesraides.lv' in url:
        # If it's already an MP4, return it directly
        if url.endswith('.mp4'):
            return url, 'mp4_video_link'
        
        # Try appending .mp4 and follow redirects - this is the most common pattern
        mp4_url = f"{url}.mp4"
        try:
            # Use allow_redirects=True to follow any redirects
            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                # If we were redirected, use the final URL
                final_url = response.url
                content_type = response.headers.get('Content-Type', '')
                if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                    logging.info(f"Found MP4 by appending .mp4 and following redirects: {final_url}")
                    return final_url, 'mp4_video_link'
                else:
                    logging.info(f"Found URL by appending .mp4, but content type is {content_type}: {final_url}")
                    # Try a GET request to see if it's actually a video
                    try:
                        get_response = requests.get(final_url, timeout=10, stream=True)
                        # Read just the first few bytes to check content type
                        get_response.raw.read(1024)
                        content_type = get_response.headers.get('Content-Type', '')
                        if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                            logging.info(f"Confirmed MP4 content type with GET request: {final_url}")
                            return final_url, 'mp4_video_link'
                    except Exception as e:
                        logging.warning(f"Error checking content with GET: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to check appended MP4 URL with redirects: {str(e)}")
        
        # Try different MP4 patterns if the simple append didn't work
        mp4_patterns = [
            f"{url}/video.mp4",
            f"{url}/download.mp4",
            f"{url}/media.mp4"
        ]
        
        for mp4_url in mp4_patterns:
            try:
                # Check if the MP4 URL exists
                response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    final_url = response.url
                    content_type = response.headers.get('Content-Type', '')
                    if 'video' in content_type or 'mp4' in content_type or 'octet-stream' in content_type:
                        logging.info(f"Found MP4: {final_url}")
                        return final_url, 'mp4_video_link'
            except Exception as e:
                logging.warning(f"Failed to check MP4 URL {mp4_url}: {str(e)}")
    
    # Use Playwright to load the page and check for video elements
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Navigate to the URL
            page.goto(url, timeout=30000)
            
            # Wait for potential video elements to load
            page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check for video elements
            video_elements = page.query_selector_all('video')
            for video in video_elements:
                src = video.get_attribute('src')
                if src and '.mp4' in src:
                    # Make sure it's a full URL
                    if src.startswith('http'):
                        mp4_url = src
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{src if src.startswith('/') else '/' + src}"
                    
                    logging.info(f"Found MP4 in video element: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Check for source elements within video tags
            source_elements = page.query_selector_all('video source')
            for source in source_elements:
                src = source.get_attribute('src')
                if src and '.mp4' in src:
                    # Make sure it's a full URL
                    if src.startswith('http'):
                        mp4_url = src
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{src if src.startswith('/') else '/' + src}"
                    
                    logging.info(f"Found MP4 in source element: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Check for iframe elements
            iframe_elements = page.query_selector_all('iframe')
            for iframe in iframe_elements:
                iframe_src = iframe.get_attribute('src')
                if iframe_src:
                    logging.info(f"Found iframe with src: {iframe_src}")
                    # We could recursively process this iframe, but for simplicity
                    # we'll just note it for now
            
            # Check network requests for MP4 files
            page.reload()
            page.wait_for_load_state('networkidle', timeout=10000)
            
            # Execute JavaScript to find video URLs in the page
            js_result = page.evaluate('''() => {
                const videoUrls = [];
                // Check for video elements
                document.querySelectorAll('video').forEach(video => {
                    if (video.src) videoUrls.push(video.src);
                });
                
                // Check for source elements
                document.querySelectorAll('source').forEach(source => {
                    if (source.src) videoUrls.push(source.src);
                });
                
                // Check for object/embed elements
                document.querySelectorAll('object, embed').forEach(obj => {
                    if (obj.data) videoUrls.push(obj.data);
                });
                
                // Look for MP4 URLs in all attributes
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    for (const attr of el.attributes) {
                        if (attr.value && attr.value.includes('.mp4')) {
                            videoUrls.push(attr.value);
                        }
                    }
                }
                
                return videoUrls;
            }''')
            
            for video_url in js_result:
                if '.mp4' in video_url:
                    # Make sure it's a full URL
                    if video_url.startswith('http'):
                        mp4_url = video_url
                    else:
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        mp4_url = f"{base_url}{video_url if video_url.startswith('/') else '/' + video_url}"
                    
                    logging.info(f"Found MP4 via JavaScript: {mp4_url}")
                    browser.close()
                    return mp4_url, 'mp4_video_link'
            
            # Get the page content and look for MP4 links
            content = page.content()
            mp4_links = re.findall(r'(https?://[^"\']+\.mp4)', content)
            if mp4_links:
                mp4_url = mp4_links[0]
                logging.info(f"Found MP4 link in page content: {mp4_url}")
                browser.close()
                return mp4_url, 'mp4_video_link'
            
            # Try to find onclick handlers that might contain video URLs
            onclick_elements = page.query_selector_all('[onclick]')
            for element in onclick_elements:
                onclick = element.get_attribute('onclick')
                if onclick and ('window.open' in onclick or '.mp4' in onclick):
                    # Extract URL from onclick
                    onclick_url_match = re.search(r"window\.open\('([^']+)'", onclick)
                    if onclick_url_match:
                        onclick_url = onclick_url_match.group(1)
                        logging.info(f"Found URL in onclick: {onclick_url}")
                        
                        # If it's an MP4 URL, return it
                        if '.mp4' in onclick_url:
                            browser.close()
                            return onclick_url, 'mp4_video_link'
                        
                        # Try appending .mp4 to the onclick URL
                        mp4_url = f"{onclick_url}.mp4"
                        try:
                            response = requests.head(mp4_url, timeout=10, allow_redirects=True)
                            if response.status_code == 200:
                                final_url = response.url
                                logging.info(f"Found MP4 by appending .mp4 to onclick URL: {final_url}")
                                browser.close()
                                return final_url, 'mp4_video_link'
                        except Exception as e:
                            logging.warning(f"Failed to check appended MP4 URL from onclick: {str(e)}")
            
        except Exception as e:
            logging.error(f"Error with Playwright for {url}: {str(e)}")
        
        browser.close()
    
    # If we can't determine the type, use generic video handler
    logging.info(f"Using generic_video_link handler as fallback for: {url}")
    return url, 'generic_video_link'
""")

    logging.info(f"Created video_link_extractors.py with the better-performing method")

def main():
    """
    Main function to test video extraction.
    """
    # Check if we have a combined matches CSV
    csv_file = 'latvia_parliament_meetings.csv'
    if not os.path.exists(csv_file):
        logging.warning(f"Could not find {csv_file}, looking for video_links.csv instead")
        csv_file = 'video_links.csv'
        if not os.path.exists(csv_file):
            logging.error("Could not find any CSV file with video links")
            return
    
    # Test video extraction
    test_video_extraction(csv_file, num_samples=5)
    
    # Create video link extractor if test results exist
    results_file = 'video_extraction_test_results.csv'
    if os.path.exists(results_file):
        create_video_link_extractor(results_file)

if __name__ == "__main__":
    main() 