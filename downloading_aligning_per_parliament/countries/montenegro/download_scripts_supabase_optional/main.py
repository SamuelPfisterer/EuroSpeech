"""Main script for downloading and processing parliamentary meeting content.

This script handles the downloading and processing of various media types (video, audio,
subtitles, transcripts) from parliamentary meetings. It supports batch processing with
logging capabilities and error handling. Supabase integration is optional.

To disable Supabase:
    - Don't set any Supabase environment variables
    
To enable Supabase:
    - Set USE_SUPABASE=true
    - Set SUPABASE_URL and SUPABASE_KEY environment variables
"""

import pandas as pd
import os
from tqdm import tqdm
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
)
import csv
from typing import Dict, List, Set, Optional, Tuple
from supabase_config import (
    create_download_entry, 
    session_exists, 
    complete_download, 
    start_download,
    SUPABASE_ENABLED
)

# Import the transcript processors individually
try:
    from transcript_processors import process_transcript_html
except ImportError:
    logging.info("HTML transcript processor not found.")
    process_transcript_html = None

try:
    from transcript_processors import process_transcript_text
except ImportError:
    logging.info("Text transcript processor not found.")
    process_transcript_text = None

# Import video link extractor
try:
    from video_link_extractors import process_video_link
except ImportError:
    logging.info("Video link extractor not found.")
    process_video_link = None

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

# Define mapping between columns and their modalities
COLUMN_TO_MODALITY = {
    # Video/Audio sources
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
    'processed_transcript_html_link': lambda url, output, **kwargs: download_and_process_with_custom_processor(
        url, output, process_transcript_html, 'html', **kwargs
    ),
    'processed_transcript_text_link': lambda url, output, **kwargs: download_and_process_with_custom_processor(
        url, output, process_transcript_text, 'txt', **kwargs
    ),
    'processed_video_link': lambda url, output: download_and_process_with_link_extractor(
        url, output, process_video_link, DOWNLOAD_FUNCTIONS
    )
}

def setup_logging(job_id: str) -> None:
    """Configure logging for the current job."""
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
    logging.info(f"Supabase integration: {'ENABLED' if SUPABASE_ENABLED else 'DISABLED'}")

def validate_processor_availability(df: pd.DataFrame) -> None:
    """Validate that required processor functions are available."""
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
    """Generate a unique session ID for the row."""
    video_id = row.get('video_id')
    transcript_id = row.get('transcript_id')
    
    if video_id and transcript_id and video_id != transcript_id:
        return f"{video_id}_{transcript_id}"
    
    return video_id or transcript_id or str(row.name)

def get_video_id(row: pd.Series) -> Optional[str]:
    """Extract just the video ID from the row."""
    return row.get('video_id')

def main(start_idx: int, end_idx: int, csv_file: str = 'danish_parliament_meetings_full_links.csv', 
         batch_storage: bool = False, update_frequency: int = 10) -> None:
    """Process and download parliamentary meeting content for a range of entries."""
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
        
        # Validate processor availability
        validate_processor_availability(df)

        # Slice DataFrame
        df = df.iloc[start_idx:end_idx]

        # Create directories
        for modality, directory in DIRECTORIES.items():
            os.makedirs(directory, exist_ok=True)
            for column in df.columns:
                if column in COLUMN_TO_MODALITY and COLUMN_TO_MODALITY[column]['modality'] == modality:
                    subfolder_path = os.path.join(directory, COLUMN_TO_MODALITY[column]['subfolder'])
                    os.makedirs(subfolder_path, exist_ok=True)

        successful_downloads = 0
        skipped_sessions = 0
        failed_downloads = {key: [] for key in DIRECTORIES}
        failed_download_links = []
        downloaded_videos = set()

        # Process each row
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing videos"):
            session_id = get_session_id(row)
            video_id = get_video_id(row)
            
            if not session_id:
                logging.error("No valid ID found in row")
                continue

            # Skip if session exists (when Supabase is enabled)
            if SUPABASE_ENABLED and session_exists(session_id):
                logging.info(f"Skipping session {session_id} - already exists in Supabase")
                skipped_sessions += 1
                continue

            # Create download entry (no-op when Supabase is disabled)
            try:
                create_download_entry(session_id)
            except Exception as e:
                logging.error(f"Failed to create Supabase entry for {session_id}: {str(e)}")
                if SUPABASE_ENABLED:
                    continue

            for column, download_func in DOWNLOAD_FUNCTIONS.items():
                if column in row and pd.notna(row[column]):
                    try:
                        column_info = COLUMN_TO_MODALITY[column]
                        modality = column_info['modality']
                        subfolder = column_info['subfolder']
                        
                        # Use video_id for filename if available
                        filename_id = video_id if modality == 'audio' and video_id else session_id
                        filename = os.path.join(
                            DIRECTORIES[modality],
                            subfolder,
                            str(filename_id)
                        )
                        
                        # Skip if video already downloaded
                        if modality == 'audio' and video_id:
                            video_path = f"{filename}.opus"
                            if video_id in downloaded_videos or os.path.exists(video_path):
                                logging.info(f"Video {video_id} already downloaded, skipping")
                                continue
                        
                        # Download with batch storage if enabled
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
                            if not with_retry(
                                func=download_func,
                                args=(row[column], filename),
                                column_info=column_info,
                                session_id=session_id
                            ):
                                failed_downloads[modality].append(session_id)
                                logging.error(f"Failed to download {column}: {session_id}")
                        
                        if modality == 'audio' and video_id:
                            downloaded_videos.add(video_id)
                    except Exception as e:
                        logging.error(f"Error processing {column} for {session_id}: {str(e)}")

            if not failed_downloads[modality]:
                successful_downloads += 1
                logging.info(f"Successfully processed all files for: {session_id}")
            else:
                failed_download_links.append(row.get('link', 'Unknown link'))
                logging.error(f"Failed to process: {session_id}")

        # Log failed downloads
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
    parser = argparse.ArgumentParser(description='Download and process parliamentary content')
    parser.add_argument("--start_idx", type=int, required=True, help="Starting index for processing")
    parser.add_argument("--end_idx", type=int, required=True, help="Ending index for processing")
    parser.add_argument("--csv_file", type=str, default='danish_parliament_meetings_full_links.csv', help="CSV file name")
    parser.add_argument("--batch_storage", action="store_true", help="Store transcripts in batch JSON files")
    parser.add_argument("--update_frequency", type=int, default=10, help="How often to update batch files (every N transcripts)")

    args = parser.parse_args()
    main(args.start_idx, args.end_idx, args.csv_file, args.batch_storage, args.update_frequency) 