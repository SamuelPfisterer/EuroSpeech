import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re
import logging
from datetime import datetime
import argparse
from download_utils import (
    with_retry, 
    download_and_process_mp4_video,
    download_and_process_srt,
    download_and_process_pdf,
    download_and_process_youtube,
    download_and_process_m3u8_video,
    download_and_process_generic_video,
    download_and_process_html,
    download_and_process_generic_m3u8_link,
    download_and_process_with_custom_processor,
    download_and_process_dynamic_html,
    download_and_process_with_link_extractor
)
import csv
from typing import Dict, List
from supabase_config import create_download_entry, session_exists

# Import the transcript processor
try:
    from ..transcript_processors import process_transcript
except ImportError:
    try:
        # Try importing from parent directory directly
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from transcript_processors import process_transcript
    except ImportError:
        logging.info("Transcript processor not found.")
        process_transcript = None

# Import video link extractor
try:
    from ..video_link_extractors import process_video_link
except ImportError:
    try:
        # Try importing from parent directory directly
        from video_link_extractors import process_video_link
    except ImportError:
        logging.info("Video link extractor not found.")
        process_video_link = None

"""Main script for downloading and processing parliamentary meeting content.

This script handles the downloading and processing of various media types (video, audio,
subtitles, transcripts) from parliamentary meetings. It supports batch processing with
logging capabilities and error handling.

Constants:
    BASE_DIR (str): Root directory of the project
    LOG_DIR (str): Directory for storing log files
    RESULTS_FILE (str): CSV file tracking download results
    CSV_DIR (str): Directory containing input CSV files
    DIRECTORIES (dict): Mapping of content types to their download directories
    DOWNLOAD_FUNCTIONS (dict): Mapping of content types to their download functions
"""

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
RESULTS_FILE = os.path.join(BASE_DIR, 'download_results.csv')
CSV_DIR = os.path.join(BASE_DIR, 'links')
DIRECTORIES = {
    'audio': os.path.join(BASE_DIR, 'downloaded_audio'),
    'subtitle': os.path.join(BASE_DIR, 'downloaded_subtitle'),
    'transcript': os.path.join(BASE_DIR, 'downloaded_transcript')
}

# Define mapping between columns and their modalities, including subfolder names
COLUMN_TO_MODALITY = {
    # Video/ Audio sources
    'mp4_video_link': {
        'modality': 'audio',
        'subfolder': 'mp4_converted'
    },
    'youtube_link': {
        'modality': 'audio',
        'subfolder': 'youtube_converted'
    },
    'm3u8_link': {
        'modality': 'audio',
        'subfolder': 'm3u8_streams'
    },
    'generic_video_link': {
        'modality': 'audio',
        'subfolder': 'generic_video'
    },
    'generic_m3u8_link': {
        'modality': 'audio',
        'subfolder': 'm3u8_streams'
    },
    'processed_video_link': {
        'modality': 'audio',
        'subfolder': 'processed_video'
    },

    # Transcript sources
    'pdf_link': {
        'modality': 'transcript',
        'subfolder': 'pdf_transcripts'
    },
    'html_link': {
        'modality': 'transcript',
        'subfolder': 'html_transcripts'
    },
    'dynamic_html_link': {
        'modality': 'transcript',
        'subfolder': 'dynamic_html_transcripts'
    },
    'processed_transcript_link': {
        'modality': 'transcript',
        'subfolder': 'processed_transcripts'  # Subfolder will be determined dynamically
    },

    # Subtitle sources
    'srt_link': {
        'modality': 'subtitle',
        'subfolder': 'srt_subtitles'
    }
}

DOWNLOAD_FUNCTIONS = {
    'mp4_video_link': download_and_process_mp4_video,
    'youtube_link': download_and_process_youtube,
    'm3u8_link': download_and_process_m3u8_video,
    'generic_video_link': download_and_process_generic_video,
    'generic_m3u8_link': download_and_process_generic_m3u8_link,
    'pdf_link': download_and_process_pdf,
    'html_link': download_and_process_html,
    'dynamic_html_link': download_and_process_dynamic_html,
    'srt_link': download_and_process_srt,
    
    # New generic transcript processor
    'processed_transcript_link': lambda url, output: download_and_process_with_custom_processor(
        url, output, process_transcript
    ),
    
    # Video link extractor
    'processed_video_link': lambda url, output: download_and_process_with_link_extractor(
        url, output, process_video_link, DOWNLOAD_FUNCTIONS
    )
}

def setup_logging(job_id: str) -> None:
    """Configure logging for the current job.

    Sets up both file and console logging handlers with appropriate formatting.

    Args:
        job_id: Unique identifier for the current job/process
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'job_{job_id}_detailed.log')
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("=== Logging initialized ===")
    logging.info(f"Log directory: {LOG_DIR}")
    logging.info(f"Log file: {log_file}")

def validate_processor_availability(df: pd.DataFrame) -> None:
    """
    Validate that required processor functions are available for the columns in the DataFrame.
    
    Args:
        df: DataFrame containing the columns to process
        
    Raises:
        ValueError: If a processor column exists but its processor function is not available
    """
    if 'processed_transcript_link' in df.columns and process_transcript is None:
        raise ValueError(
            "DataFrame contains 'processed_transcript_link' column but no transcript processor "
            "is available. Please implement process_transcript in transcript_processors.py"
        )

def main(start_idx: int, end_idx: int, csv_file: str = 'danish_parliament_meetings_full_links.csv') -> None:
    """Process and download parliamentary meeting content for a range of entries.

    Downloads various media types (video, audio, subtitles, transcripts) for parliamentary
    meetings specified in the input CSV file. Handles batch processing with comprehensive
    logging and error tracking. When both video_id and transcript_id are present,
    files are stored under their respective IDs.

    Args:
        start_idx: Starting index in the CSV file to process
        end_idx: Ending index in the CSV file to process
        csv_file: Name of the input CSV file containing meeting information

    Raises:
        FileNotFoundError: If the specified CSV file doesn't exist
        Exception: For other critical errors during processing
    """
    job_id = os.getenv('SLURM_ARRAY_TASK_ID', 'interactive')
    setup_logging(job_id)
    logging.info(f"Starting processing for videos {start_idx} to {end_idx}")

    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'failed_component'])

    try:
        # Read CSV file
        csv_path = os.path.join(CSV_DIR, csv_file)
        logging.info(f"Attempting to read CSV from: {csv_path}")
        if not os.path.exists(csv_path):
            logging.error(f"CSV file does not exist at: {csv_path}")
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Validate processor availability before starting
        validate_processor_availability(df)

        # Slice DataFrame to process specified range
        df = df.iloc[start_idx:end_idx]

        # Create main directories and subfolders
        for modality, directory in DIRECTORIES.items():
            os.makedirs(directory, exist_ok=True)
            # Create subfolders for each column type that exists in the CSV
            for column in df.columns:
                if column in COLUMN_TO_MODALITY and COLUMN_TO_MODALITY[column]['modality'] == modality:
                    subfolder_path = os.path.join(directory, COLUMN_TO_MODALITY[column]['subfolder'])
                    os.makedirs(subfolder_path, exist_ok=True)

        successful_downloads = 0
        skipped_sessions = 0
        failed_downloads = {key: [] for key in DIRECTORIES}
        failed_download_links = []

        # Process each row in the DataFrame
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
            video_id = row.get('video_id')
            transcript_id = row.get('transcript_id')
            
            if not (video_id or transcript_id):
                logging.error("No valid ID found in row. Ensure 'video_id' or 'transcript_id' is present.")
                continue

            # Use video_id for session tracking in Supabase if present, otherwise transcript_id
            session_id = video_id or transcript_id
            
            # Check if session already exists in Supabase
            if session_exists(session_id):
                logging.info(f"Skipping session {session_id} - already exists in Supabase")
                skipped_sessions += 1
                continue

            # Create download entry in Supabase
            try:
                create_download_entry(session_id)
            except Exception as e:
                logging.error(f"Failed to create Supabase entry for {session_id}: {str(e)}")
                continue

            for column, download_func in DOWNLOAD_FUNCTIONS.items():
                if column in row and pd.notna(row[column]):
                    try:
                        column_info = COLUMN_TO_MODALITY[column]
                        modality = column_info['modality']
                        subfolder = column_info['subfolder']
                        
                        # If both IDs exist, use transcript_id for transcripts and video_id for videos
                        # If only one ID exists, use that ID for everything
                        if video_id and transcript_id:
                            output_id = transcript_id if modality == 'transcript' else video_id
                        else:
                            output_id = video_id or transcript_id
                        
                        # Create filename with subfolder
                        filename = os.path.join(
                            DIRECTORIES[modality],
                            subfolder,
                            str(output_id)
                        )
                        
                        if not with_retry(
                            func=download_func,
                            args=(row[column], filename),
                            column_info=column_info,
                            session_id=session_id
                        ):
                            failed_downloads[modality].append(output_id)
                            logging.error(f"Failed to download {column}: {output_id}")
                    except Exception as e:
                        logging.error(f"Error processing {column} for {output_id}: {str(e)}")

            if not failed_downloads[modality]:
                successful_downloads += 1
                logging.info(f"Successfully processed all files for: {session_id}")
            else:
                failed_download_links.append(row.get('link', 'Unknown link'))
                logging.error(f"Failed to process: {session_id}")

        # Log failed downloads to results file
        with open(RESULTS_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            for component, failed_ids in failed_downloads.items():
                for id_value in failed_ids:
                    writer.writerow([id_value, component])

        logging.info(f"\nProcessed rows {start_idx} to {end_idx}")
        logging.info(f"Successfully processed: {successful_downloads}")
        logging.info(f"Skipped sessions: {skipped_sessions}")
        logging.info(f"Failed downloads: {sum(len(ids) for ids in failed_downloads.values())}")

        if failed_download_links:
            logging.info("Failed URLs:")
            for url in failed_download_links:
                logging.info(url)

    except Exception as e:
        logging.error(f"Critical error in main process: {str(e)}")
        raise e

if __name__ == "__main__":
    """Script entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(description='Download and process YouTube videos')
    parser.add_argument("--start_idx", type=int, required=True, help="Starting index for processing")
    parser.add_argument("--end_idx", type=int, required=True, help="Ending index for processing")
    parser.add_argument("--csv_file", type=str, default='danish_parliament_meetings_full_links.csv', help="CSV file name")

    args = parser.parse_args()
    main(args.start_idx, args.end_idx, args.csv_file)