import pandas as pd
from getting_speech_segments import extract_speeches_with_playwright
from pathlib import Path
import logging
from tqdm import tqdm
import time
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='transcript_processing.log'
)

START_YEAR = 2017
MIN_DELAY = 2  # Minimum delay in seconds
MAX_DELAY = 4  # Maximum delay in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests

def load_transcript_links():
    """Load the transcript links from CSV file."""
    df = pd.read_csv("transcript_links_with_dates.csv")
    
    # Extract date components and assign them to separate columns
    date_components = df['date'].str.extract(r'(\d{1,2})\. (\w+) (\d{4})')
    df[['day', 'month', 'year']] = date_components  # Instead of assigning directly to 'date'
    
    # Create month mapping for Norwegian months
    month_map = {
        'januar': 1, 'februar': 2, 'mars': 3, 'april': 4, 'mai': 5, 'juni': 6,
        'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    
    # Convert month names to numbers
    df['month'] = df['month'].map(month_map)
    
    # Combine into datetime
    df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
    
    # Filter for dates from 2015 onwards
    df = df[df['date'].dt.year >= START_YEAR]
    logging.info(f"Loaded {len(df)} transcript links from 2015 onwards")
    
    return df[["link", "date"]].to_dict("records")

def process_transcripts_by_year():
    """Process all transcripts from 2015 onwards and save them by year."""
    transcript_links = load_transcript_links()
    
    # Group links by year
    year_groups = {}
    for link in transcript_links:
        year = link["date"].year
        if year not in year_groups:
            year_groups[year] = []
        year_groups[year].append(link)
    
    # Process each year
    for year, links in year_groups.items():
        all_speeches = []
        logging.info(f"Starting processing {len(links)} transcripts for {year}")
        
        # Process each transcript with a progress bar
        for link_data in tqdm(links, desc=f"Processing {year}"):
            retries = 0
            success = False
            
            while retries < MAX_RETRIES and not success:
                try:
                    # Random delay between requests
                    delay = random.uniform(MIN_DELAY, MAX_DELAY)
                    time.sleep(delay)
                    
                    speeches = extract_speeches_with_playwright(link_data["link"])
                    # Add transcript URL and date to each speech
                    for speech in speeches:
                        speech["transcript_url"] = link_data["link"]
                        speech["transcript_date"] = link_data["date"]
                    all_speeches.extend(speeches)
                    success = True
                    
                except Exception as e:
                    retries += 1
                    logging.error(f"Attempt {retries} failed for {link_data['link']}: {str(e)}")
                    if retries < MAX_RETRIES:
                        # Exponential backoff for retries
                        wait_time = (2 ** retries) + random.uniform(1, 3)
                        logging.info(f"Waiting {wait_time:.2f} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        logging.error(f"Failed to process {link_data['link']} after {MAX_RETRIES} attempts")
        
        # Save to CSV if we have speeches
        if all_speeches:
            output_dir = Path("processed_speeches")
            output_dir.mkdir(exist_ok=True)
            
            df = pd.DataFrame(all_speeches)
            output_file = output_dir / f"speeches_{year}.csv"
            df.to_csv(output_file, index=False)
            logging.info(f"Saved {len(all_speeches)} speeches for {year} to {output_file}")

if __name__ == "__main__":
    process_transcripts_by_year() 