import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re
import logging
from datetime import datetime
import argparse
from download_utils import get_transcript_id, download_and_process_audio, with_retry, get_bundestag_video_id, download_and_process_mp4_video, download_and_process_srt, download_and_process_pdf
import csv
from typing import Dict, List





def setup_logging(job_id):
    # Get base directory (Germany folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create logs directory with absolute path
    log_dir = os.path.abspath(os.path.join(base_dir, 'logs'))
    os.makedirs(log_dir, exist_ok=True)

    # Use absolute path for log file
    log_file = os.path.abspath(os.path.join(log_dir, f'job_{job_id}_detailed.log'))
    
    # Clear any existing handlers
    logging.getLogger().handlers = []
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Now it's safe to log
    logging.info("=== Logging initialized ===")
    logging.info(f"Log directory: {log_dir}")
    logging.info(f"Log file: {log_file}")

    

def main(start_idx, end_idx, csv_file = 'germany_comitee_links_with_srt.csv'):
    # Set up logging
    job_id = os.getenv('SLURM_ARRAY_TASK_ID', 'interactive')
    setup_logging(job_id)
    
    logging.info(f"Starting processing for videos {start_idx} to {end_idx}")

    # Make sure that the file to store the results exist
    results_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'download_results.csv')
    if not os.path.exists(results_file):
        with open(results_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['video_id', 'failed_component'])

    
    try:

        try:
            # Get absolute paths for debugging
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            parent_dir = os.path.dirname(script_dir)  # Germany folder
            
            csv_path = os.path.join(
                parent_dir,
                'Links',
                csv_file
            )
            logging.info(f"Attempting to read CSV from: {csv_path}")
            
            # Verify file exists
            if not os.path.exists(csv_path):
                logging.error(f"CSV file does not exist at: {csv_path}")
                raise FileNotFoundError(f"CSV file not found at: {csv_path}")
                
            df = pd.read_csv(csv_path)
        except Exception as e:
            logging.error(f"Error reading CSV file: {str(e)}")
            raise e

        df = df.iloc[start_idx:end_idx]
        
        # Ensure directories exist
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
        # Setup directories in correct location
        directories = [
            os.path.join(base_dir, 'downloaded_audio'),
            os.path.join(base_dir, 'downloaded_subtitle'),
            os.path.join(base_dir, 'downloaded_transcript')
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        successful_downloads = 0
        failed_downloads = {
            'video': [],
            'subtitle': [],
            'transcript': []
        }
        failed_download_links = []

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
            video_id = get_bundestag_video_id(row['link'])
            if not video_id:
                logging.error(f"Could not extract video ID from link: {row['link']}")
                continue

            filenames = {
                'audio': os.path.abspath(os.path.join(base_dir, 'downloaded_audio', str(video_id))),
                'subtitle': os.path.abspath(os.path.join(base_dir, 'downloaded_subtitle', str(video_id))),
                'transcript': os.path.abspath(os.path.join(base_dir, 'downloaded_transcript', str(video_id)))
            }
            logging.info(f"Processing video: {video_id}")

            success = True
            try:
                # Video download
                
                if not with_retry(download_and_process_mp4_video, row['video_link'], filenames['audio']):
                    failed_downloads['video'].append(video_id)
                    logging.error(f"Failed to download video: {video_id}")
                    success = False
                
                # Subtitle download (only if video succeeded)
                if success and row.get('subtitle_link'):
                    if not with_retry(download_and_process_srt, row['subtitle_link'], filenames['subtitle']):
                        failed_downloads['subtitle'].append(video_id)
                        logging.error(f"Failed to download subtitles: {video_id}")
                        success = False
                
                # Transcript download (only if video succeeded)
                if success and row.get('transcript_link'):
                    if not with_retry(download_and_process_pdf, row['transcript_link'], filenames['transcript']):
                        failed_downloads['transcript'].append(video_id)
                        logging.error(f"Failed to download transcript: {video_id}")
                        success = False

                # Update success counter
                if success:
                    successful_downloads += 1
                    logging.info(f"Successfully processed all files for: {video_id}")


                else:
                    failed_download_links.append(row['link'])
                    logging.error(f"Failed to process: {video_id}")
            except Exception as e:
                failed_downloads['video'].append(video_id)
                failed_download_links.append(row['link'])
                logging.error(f"Error processing {video_id}: {str(e)}")

        # add the failed donwloads to a file
        '''
        with open(results_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write failed downloads
            for component, failed_ids in failed_downloads.items():
                for video_id in failed_ids:
                    writer.writerow([
                        video_id,
                        component
                    ])
        '''


        logging.info(f"\nProcessed rows {start_idx} to {end_idx}")
        logging.info(f"Successfully processed: {successful_downloads}")
        logging.info(f"Failed downloads: {len(failed_downloads)}")
        
        if failed_downloads:
            logging.info("Failed URLs:")
            for url in failed_download_links:
                logging.info(url)
                
    except Exception as e:
        logging.error(f"Critical error in main process: {str(e)}")
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and process YouTube videos')
    parser.add_argument("--start_idx", type=int, required=True, help="Starting index for processing")
    parser.add_argument("--end_idx", type=int, required=True, help="Ending index for processing")
    
    args = parser.parse_args()
    
    main(args.start_idx, args.end_idx)