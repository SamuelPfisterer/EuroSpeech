import pandas as pd
import argparse
import logging
import time
import os
from typing import Optional
from download_utils import download_and_process_youtube

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('yt_download.log'),
        logging.StreamHandler()
    ]
)

def download_videos(
    csv_path: str,
    link_column: str,
    id_column: str = "video_id",
    start_row: Optional[int] = None,
    end_row: Optional[int] = None
) -> None:
    """
    Download videos from links in a CSV file using yt-dlp.
    
    Args:
        csv_path: Path to the CSV file
        link_column: Name of the column containing video links
        id_column: Name of the column containing video IDs (default: "video_id")
        start_row: Starting row index (0-based, inclusive)
        end_row: Ending row index (0-based, inclusive)
    """
    # Create temp directory if it doesn't exist
    temp_dir = 'temp_downloaded_audio'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Validate column names
    if link_column not in df.columns:
        raise ValueError(f"Column '{link_column}' not found in CSV file")
    
    # Check for video_id or transcript_id column
    if id_column not in df.columns and id_column == "video_id":
        if "transcript_id" in df.columns:
            logging.info("Using 'transcript_id' column instead of 'video_id'")
            id_column = "transcript_id"
        else:
            raise ValueError("Neither 'video_id' nor 'transcript_id' column found in CSV file")
    
    # Select rows based on range
    if start_row is not None and end_row is not None:
        df = df.iloc[start_row:end_row + 1]
    
    total_videos = len(df)
    successful_downloads = 0
    failed_downloads = 0
    
    # Download each video
    for idx, row in df.iterrows():
        video_link = row[link_column]
        video_id = row[id_column]
        current_video = df.index.get_loc(idx) + 1
        
        logging.info(f"\nProcessing video {current_video}/{total_videos}")
        logging.info(f"Video ID: {video_id}")
        logging.info(f"URL: {video_link}")
        
        start_time = time.time()
        
        try:
            success = download_and_process_youtube(video_link, video_id)
            elapsed_time = time.time() - start_time
            
            if success:
                successful_downloads += 1
                logging.info(f"✓ Success: {video_id} ({elapsed_time:.2f}s)")
            else:
                failed_downloads += 1
                logging.error(f"✗ Failed: {video_id} ({elapsed_time:.2f}s)")
                
        except Exception as e:
            failed_downloads += 1
            elapsed_time = time.time() - start_time
            logging.error(f"✗ Error processing {video_id} ({elapsed_time:.2f}s): {str(e)}")
    
    # Print summary
    logging.info("\nDownload Summary:")
    logging.info(f"Total videos processed: {total_videos}")
    logging.info(f"Successful downloads: {successful_downloads}")
    logging.info(f"Failed downloads: {failed_downloads}")

def main():
    # Hardcoded values
    csv_path = "scraping-parliaments-internally\montenegro\montenegro_urls.csv"
    column_name = "youtube_link"
    start_row = 2
    end_row = 2
    
    download_videos(
        csv_path,
        column_name,
        start_row=start_row,
        end_row=end_row
    )

if __name__ == "__main__":
    main()
