import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re
import logging
from datetime import datetime
import argparse
from download_utils import get_transcript_id, get_youtube_id, download_and_process_audio, download_and_process_with_retry

def setup_logging(job_id):
    log_dir = 'logs'
    #os.makedirs(log_dir, exist_ok=True)
    # we have to go one folder up
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    '''
    also here we have to go one folder up
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{log_dir}/job_{job_id}_detailed.log'),
            logging.StreamHandler()
        ]
    )'''
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f'job_{job_id}_detailed.log')),
            logging.StreamHandler()
        ]
    )
    

def main(start_idx, end_idx, csv_file = 'transcript_link_with_exactly_one_youtube_link.csv'):
    # Set up logging
    job_id = os.getenv('SLURM_ARRAY_TASK_ID', 'interactive')
    setup_logging(job_id)
    
    logging.info(f"Starting processing for videos {start_idx} to {end_idx}")
    
    try:

        try: 
            csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), csv_file)
            df = pd.read_csv(csv_path)
        except Exception as e:
            df = pd.read_csv(csv_file)

        df = df.iloc[start_idx:end_idx]
        
        os.makedirs('downloaded_audio', exist_ok=True)
        successful_downloads = 0
        failed_downloads = []

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
            transcript_id = get_transcript_id(row['transcript_link'])
            youtube_id = get_youtube_id(row['youtube_link'])
            
            if youtube_id:
                output_filename = f'downloaded_audio/{transcript_id}_{youtube_id}'
                logging.info(f"Processing video: {youtube_id}")
                try:
                    if download_and_process_with_retry(row['youtube_link'], output_filename):
                        successful_downloads += 1
                        logging.info(f"Successfully processed: {youtube_id}")
                    else:
                        failed_downloads.append(row['youtube_link'])
                        logging.error(f"Failed to process: {youtube_id}")
                except Exception as e:
                    failed_downloads.append(row['youtube_link'])
                    logging.error(f"Error processing {youtube_id}: {str(e)}")

        logging.info(f"\nProcessed rows {start_idx} to {end_idx}")
        logging.info(f"Successfully processed: {successful_downloads}")
        logging.info(f"Failed downloads: {len(failed_downloads)}")
        
        if failed_downloads:
            logging.info("Failed URLs:")
            for url in failed_downloads:
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