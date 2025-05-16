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
    download_and_process_with_link_extractor,
    download_and_process_doc,
    get_file_size,
    get_video_duration,
    download_and_process_mp3
)
import csv
from typing import Dict, List, Set, Optional, Tuple
from supabase_config import create_download_entry, session_exists, complete_download, start_download

# Import the transcript processors individually
# Note: Users need to implement these in their transcript_processors.py
try:
    from ..transcript_processors import process_transcript_html
except ImportError:
    try:
        # Try importing from parent directory directly
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from transcript_processors import process_transcript_html
    except ImportError:
        logging.info("HTML transcript processor not found.")
        process_transcript_html = None

try:
    from ..transcript_processors import process_transcript_text
except ImportError:
    try:
        # Try importing from parent directory directly
        from transcript_processors import process_transcript_text
    except ImportError:
        logging.info("Text transcript processor not found.")
        process_transcript_text = None

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

    # New processed transcript types
    'processed_transcript_html_link': {
        'modality': 'transcript',
        'subfolder': 'processed_html_transcripts'
    },
    'processed_transcript_text_link': {
        'modality': 'transcript',
        'subfolder': 'processed_text_transcripts'
    },

    # Subtitle sources
    'srt_link': {
        'modality': 'subtitle',
        'subfolder': 'srt_subtitles'
    },

    # New Word document source
    'doc_link': {
        'modality': 'transcript',
        'subfolder': 'doc_transcripts'
    },

    # New MP3 audio source
    'mp3_link': {
        'modality': 'audio',
        'subfolder': 'mp3_audio'
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
    
    # New processed transcript functions - update these to accept and pass additional kwargs
    'processed_transcript_html_link': lambda url, output, **kwargs: download_and_process_with_custom_processor(
        url, output, process_transcript_html, 'html', **kwargs
    ),
    'processed_transcript_text_link': lambda url, output, **kwargs: download_and_process_with_custom_processor(
        url, output, process_transcript_text, 'txt', **kwargs
    ),
    
    # New processed video function
    'processed_video_link': lambda url, output: download_and_process_with_link_extractor(
        url, output, process_video_link, DOWNLOAD_FUNCTIONS
    ),

    # New Word document function
    'doc_link': download_and_process_doc,

    # New MP3 audio function
    'mp3_link': download_and_process_mp3
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
    if 'processed_transcript_html_link' in df.columns and process_transcript_html is None:
        raise ValueError(
            "DataFrame contains 'processed_transcript_html_link' column but no HTML processor function "
            "is available. Please implement process_transcript_html in transcript_processors.py"
        )
    
    if 'processed_transcript_text_link' in df.columns and process_transcript_text is None:
        raise ValueError(
            "DataFrame contains 'processed_transcript_text_link' column but no text processor function "
            "is available. Please implement process_transcript_text in transcript_processors.py"
        )

def get_session_id(row: pd.Series) -> str:
    """
    Generate a unique session ID for the row.
    
    If both video_id and transcript_id are present and different, 
    use a combination of both to ensure uniqueness.
    
    Args:
        row: DataFrame row containing session information
        
    Returns:
        Unique session ID string
    """
    video_id = row.get('video_id')
    transcript_id = row.get('transcript_id')
    
    if video_id and transcript_id and video_id != transcript_id:
        return f"{video_id}_{transcript_id}"
    
    return video_id or transcript_id or str(row.name)  # Fallback to row index if no IDs

def get_video_id(row: pd.Series) -> Optional[str]:
    """
    Extract just the video ID from the row.
    
    Args:
        row: DataFrame row containing session information
        
    Returns:
        Video ID string or None if not present
    """
    return row.get('video_id')

def main(start_idx: int, end_idx: int, csv_file: str = 'danish_parliament_meetings_full_links.csv', 
         batch_storage: bool = False, update_frequency: int = 10) -> None:
    """Process and download parliamentary meeting content for a range of entries.

    Downloads various media types (video, audio, subtitles, transcripts) for parliamentary
    meetings specified in the input CSV file. Handles batch processing with comprehensive
    logging and error tracking.

    Args:
        start_idx: Starting index in the CSV file to process
        end_idx: Ending index in the CSV file to process
        csv_file: Name of the input CSV file containing meeting information
        batch_storage: Whether to use batch storage for transcripts
        update_frequency: How often to update batch files (every N transcripts)

    Raises:
        FileNotFoundError: If the specified CSV file doesn't exist
        Exception: For other critical errors during processing
    """
    job_id = os.getenv('SLURM_ARRAY_TASK_ID', 'interactive')
    setup_logging(job_id)
    logging.info(f"Starting processing for videos {start_idx} to {end_idx}")
    
    if batch_storage:
        logging.info(f"Batch storage enabled. Update frequency: every {update_frequency} transcripts")

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
        
        # Track already downloaded videos to avoid duplicates
        downloaded_videos = set()

        # Process each row in the DataFrame
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
            # Generate a unique session ID for this row
            session_id = get_session_id(row)
            
            # Get the video ID (may be the same across multiple rows)
            video_id = get_video_id(row)
            
            if not session_id:
                logging.error("No valid ID found in row. Ensure 'video_id' or 'transcript_id' is present.")
                continue

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
                        
                        # For audio/video content, use video_id for the filename if available
                        # This ensures all transcripts reference the same video file
                        if modality == 'audio' and video_id:
                            filename_id = video_id
                        else:
                            filename_id = session_id
                            
                        # Create filename with subfolder
                        filename = os.path.join(
                            DIRECTORIES[modality],
                            subfolder,
                            str(filename_id)
                        )
                        
                        # For audio/video content, check if we've already downloaded this video
                        if modality == 'audio' and video_id:
                            # Check if this video has already been downloaded
                            video_path = f"{filename}.opus"
                            if video_id in downloaded_videos or os.path.exists(video_path):
                                logging.info(f"Video {video_id} already downloaded, skipping download for session {session_id}")
                                
                                # Mark the video as completed in Supabase with 0 duration
                                # First mark as downloading (required by Supabase workflow)
                                start_download(session_id, 'video')
                                
                                # Then mark as completed with 0 duration for this session
                                # (actual metrics are recorded with the first download)
                                zero_metrics = {
                                    'duration': 0,  # 0 seconds duration for duplicate videos
                                    'size': 0       # 0 bytes size for duplicate videos
                                }
                                complete_download(session_id, 'video', zero_metrics)
                                
                                # Continue to next column (skip the download)
                                continue
                        
                        # For transcript processors that support batch storage
                        if batch_storage and column in ['processed_transcript_html_link', 'processed_transcript_text_link']:
                            if not with_retry(
                                func=lambda *args: download_func(
                                    *args, 
                                    batch_storage=batch_storage,
                                    update_frequency=update_frequency,
                                    start_idx=start_idx,
                                    end_idx=end_idx
                                ),
                                args=(row[column], filename),
                                column_info=column_info,
                                session_id=session_id
                            ):
                                failed_downloads[modality].append(session_id)
                                logging.error(f"Failed to download {column}: {session_id}")
                        else:
                            # Regular download function call
                            if not with_retry(
                                func=download_func,
                                args=(row[column], filename),
                                column_info=column_info,
                                session_id=session_id
                            ):
                                failed_downloads[modality].append(session_id)
                                logging.error(f"Failed to download {column}: {session_id}")
                        
                        if modality == 'audio' and video_id:
                            # Mark this video as downloaded
                            downloaded_videos.add(video_id)
                    except Exception as e:
                        logging.error(f"Error processing {column} for {session_id}: {str(e)}")

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
    parser.add_argument("--batch_storage", action="store_true", help="Store transcripts in batch JSON files")
    parser.add_argument("--update_frequency", type=int, default=10, help="How often to update batch files (every N transcripts)")

    args = parser.parse_args()
    main(args.start_idx, args.end_idx, args.csv_file, args.batch_storage, args.update_frequency)