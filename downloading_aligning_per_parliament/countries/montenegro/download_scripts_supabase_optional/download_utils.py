"""Utility functions for downloading and processing parliamentary content.

This module provides functions for downloading and processing various types of content
(video, audio, transcripts, etc.) from parliamentary websites. It includes retry logic
and optional Supabase integration for tracking download progress.
"""

import subprocess
import os
import shutil
import time
import logging
import random
import requests
from typing import List, Optional, Protocol, Union, Tuple, Dict, Any
import csv
from datetime import datetime
from supabase_config import (
    start_download, 
    complete_download, 
    fail_download,
    SUPABASE_ENABLED
)
from playwright.sync_api import sync_playwright

# Proxy configuration
PROXY_URL = "http://island:ausgeTrickst=)@168.151.206.16:20000"
PROXY_CONFIG = {'http': PROXY_URL, 'https': PROXY_URL}

try:
    from batch_storage import BatchStorageManager
except ImportError:
    BatchStorageManager = None
    logging.info("BatchStorageManager not available. Batch storage will be disabled.")

class TranscriptProcessor(Protocol):
    """Protocol defining the interface for transcript processing functions."""
    def __call__(self, url: str) -> Union[str, bytes]:
        """Process a transcript URL and return the content."""
        ...

class VideoLinkExtractor(Protocol):
    """Protocol defining the interface for video link extraction functions."""
    def __call__(self, url: str) -> Tuple[str, str]:
        """Process a video page URL and return the actual downloadable link and its type."""
        ...

# Map local modalities to Supabase modalities
SUPABASE_MODALITY_MAPPING = {
    'audio': 'video',      # All audio/video content maps to video in Supabase
    'subtitle': 'video',   # Subtitles are associated with videos
    'transcript': 'transcript'  # Transcripts map directly
}

def add_download_delay():
    """Add a random delay between downloads to avoid overwhelming the server."""
    if random.random() < 0.1:  # 10% chance of a longer delay
        delay = random.uniform(15, 20)
    else:
        delay = random.uniform(8, 12)
    time.sleep(delay)

def get_video_duration(file_path: str) -> int:
    """Get video duration in seconds using ffprobe."""
    try:
        if not file_path.endswith('.opus'):
            file_path = f"{file_path}.opus"
            
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        output = subprocess.check_output(cmd).decode().strip()
        return int(float(output))
    except Exception as e:
        logging.error(f"Failed to get video duration: {str(e)}")
        return 0

def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    try:
        if not file_path.endswith('.opus'):
            file_path = f"{file_path}.opus"
            
        return os.path.getsize(file_path)
    except Exception as e:
        logging.error(f"Failed to get file size: {str(e)}")
        return 0

def with_retry(func, args, column_info, session_id):
    """Generic retry wrapper with optional Supabase integration."""
    wait_times = [30, 60, 120, 180, 300]
    modality = column_info['modality']
    supabase_modality = SUPABASE_MODALITY_MAPPING[modality]
    
    # Start download tracking (no-op if Supabase is disabled)
    if SUPABASE_ENABLED:
        start_download(session_id, supabase_modality)
    
    for attempt, wait_time in enumerate(wait_times, 1):
        try:
            result = func(*args)
            
            if result is False:
                error_msg = f"Download failed for {args}"
                logging.warning(f"Attempt {attempt} failed: {error_msg}")
            elif isinstance(result, str):
                error_msg = result
                logging.warning(f"Attempt {attempt} failed: {error_msg}")
                if "HTTP Error 404" in error_msg:
                    if SUPABASE_ENABLED:
                        fail_download(session_id, supabase_modality, error_msg, retry_count=attempt)
                    logging.error(f"All attempts failed for {args} after {len(wait_times)} tries.")
                    return False
            else:
                # Success case
                if SUPABASE_ENABLED:
                    metrics = None
                    if modality == 'audio':  # Only collect metrics for audio files
                        output_path = args[1]
                        metrics = {
                            'duration': get_video_duration(output_path),
                            'size': get_file_size(output_path)
                        }
                    complete_download(session_id, supabase_modality, metrics)
                return True
                
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
                continue
            else:
                if SUPABASE_ENABLED:
                    fail_download(session_id, supabase_modality, error_msg, retry_count=attempt)
                logging.error(f"All attempts failed after {len(wait_times)} tries: {error_msg}")
                raise Exception(error_msg)
            
        except Exception as e:
            error_msg = str(e)
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Attempt {attempt} failed for {args}: {error_msg}. Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
            else:
                if SUPABASE_ENABLED:
                    fail_download(session_id, supabase_modality, error_msg, retry_count=attempt)
                logging.error(f"All attempts failed for {args} after {len(wait_times)} tries.")
                raise e
    
    return False

# The rest of the download functions remain unchanged as they don't interact with Supabase directly
# They are called through with_retry which handles the Supabase integration

def download_and_process_mp4_video(mp4_link: str, output_filename: str) -> bool:
    """Download MP4 and convert to opus audio format."""
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_opus = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.opus')
        final_opus = f'{output_filename}.opus'

        download_command = [
            'ffmpeg',
            '-i', mp4_link,
            '-vn',
            '-c:a', 'libopus',
            '-b:a', '96k',
            '-ac', '1',
            '-ar', '24000',
            '-application', 'voip',
            temp_opus
        ]
        
        logging.info(f"Starting download for: {mp4_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
        
        shutil.move(temp_opus, final_opus)
        logging.info(f"Successfully processed: {mp4_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {mp4_link}: {str(e)}")
        return False
    finally:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

# ... [Rest of the download functions remain unchanged] ...

# Note: I'm not including all the download functions here as they remain unchanged
# They don't interact with Supabase directly, so they work the same way
# The Supabase integration is handled entirely through the with_retry function 