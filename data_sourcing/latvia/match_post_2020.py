from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import re
import csv
import time
from tqdm import tqdm

def extract_video_links(html_content, transcript_url):
    """
    Extract video links from the transcript page HTML content.
    Looks for video links in the table structure as shown in the example.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    video_links = []
    
    # Look for tables that might contain video links
    tables = soup.find_all('table')
    
    for table in tables:
        # Check if this table contains video links
        links = table.find_all('a')
        for link in links:
            # Check if this is a video link (they typically have an onclick attribute with window.open)
            onclick = link.get('onclick')
            if onclick and 'window.open' in onclick:
                # Extract the URL from the onclick attribute
                url_match = re.search(r"window\.open\('([^']+)'", onclick)
                if url_match:
                    video_url = url_match.group(1)
                    
                    # Extract the time if available
                    time_text = link.get_text(strip=True)
                    
                    # Add to our list of video links
                    video_links.append({
                        'video_url': video_url,
                        'time': time_text,
                        'transcript_url': transcript_url
                    })
    
    return video_links

def scrape_transcript_page(url, page):
    """
    Scrape a transcript page to extract video links.
    """
    try:
        page.goto(url)
        # Wait for the content to load
        page.wait_for_selector('table', timeout=10000)
        html_content = page.content()
        return html_content
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    # Read the transcript links CSV
    transcripts_df = pd.read_csv('transcript_links.csv')
    
    # Convert date column to datetime
    transcripts_df['Date'] = pd.to_datetime(transcripts_df['Date'])
    
    # Filter for transcripts from 2020 onwards
    post_2020_transcripts = transcripts_df[transcripts_df['Date'] >= '2020-01-01']
    
    print(f"Found {len(post_2020_transcripts)} transcript links from 2020 onwards")
    
    # Prepare to store results
    results = []
    transcripts_without_videos = []
    
    # Counters for hit rate calculation
    total_processed = 0
    transcripts_with_videos = 0
    
    # Use playwright to scrape each transcript page
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Process each transcript link with a progress bar
        pbar = tqdm(total=len(post_2020_transcripts), desc="Processing transcripts")
        
        for index, row in post_2020_transcripts.iterrows():
            transcript_url = row['URL']
            transcript_date = row['Date']
            
            # Scrape the transcript page
            html_content = scrape_transcript_page(transcript_url, page)
            
            total_processed += 1
            
            if html_content:
                # Extract video links
                video_links = extract_video_links(html_content, transcript_url)
                
                if video_links:
                    # Add to results
                    for video_link in video_links:
                        results.append({
                            'transcript_date': transcript_date,
                            'transcript_url': transcript_url,
                            'video_url': video_link['video_url'],
                            'video_time': video_link['time']
                        })
                    transcripts_with_videos += 1
                else:
                    # Record transcripts without videos
                    transcripts_without_videos.append({
                        'transcript_date': transcript_date,
                        'transcript_url': transcript_url,
                        'reason': 'No video links found'
                    })
            else:
                # Record transcripts that couldn't be scraped
                transcripts_without_videos.append({
                    'transcript_date': transcript_date,
                    'transcript_url': transcript_url,
                    'reason': 'Failed to scrape page'
                })
            
            # Update hit rate in the progress bar
            hit_rate = (transcripts_with_videos / total_processed) * 100 if total_processed > 0 else 0
            pbar.set_description(f"Processing transcripts | Hit rate: {hit_rate:.2f}%")
            pbar.update(1)
            
            # Be nice to the server
            time.sleep(1)
        
        pbar.close()
        browser.close()
    
    # Save results to CSV
    if results:
        results_df = pd.DataFrame(results)
        output_file = 'post_2020_matches.csv'
        results_df.to_csv(output_file, index=False)
        print(f"Saved {len(results)} video-transcript matches to {output_file}")
        
        # Print some statistics
        transcript_count = len(results_df['transcript_url'].unique())
        video_count = len(results_df['video_url'].unique())
        print(f"Found {video_count} unique videos linked from {transcript_count} transcripts")
    else:
        print("No matches found")
    
    # Save transcripts without videos to CSV
    if transcripts_without_videos:
        no_videos_df = pd.DataFrame(transcripts_without_videos)
        no_videos_file = 'transcripts_without_videos.csv'
        no_videos_df.to_csv(no_videos_file, index=False)
        print(f"Saved {len(transcripts_without_videos)} transcripts without videos to {no_videos_file}")
    
    # Final hit rate
    final_hit_rate = (transcripts_with_videos / total_processed) * 100 if total_processed > 0 else 0
    print(f"\nFinal hit rate: {final_hit_rate:.2f}%")
    print(f"Transcripts with videos: {transcripts_with_videos}/{total_processed}")

if __name__ == "__main__":
    main()
