import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re
import shutil
import time
import logging
import yt_dlp
import random
import requests
from typing import List, Optional, Protocol, Union, Tuple, Dict, Any
import csv
from datetime import datetime
from supabase_config import start_download, complete_download, fail_download
from playwright.sync_api import sync_playwright

# Proxy configuration
PROXY_URL = "http://island:ausgeTrickst=)@168.151.206.16:20000"
PROXY_CONFIG = {'http': PROXY_URL, 'https': PROXY_URL}

try:
    from batch_storage import BatchStorageManager
except ImportError:
    # Try relative import
    try:
        from .batch_storage import BatchStorageManager
    except ImportError:
        BatchStorageManager = None
        logging.info("BatchStorageManager not available. Batch storage will be disabled.")

class TranscriptProcessor(Protocol):
    """Protocol defining the interface for transcript processing functions."""
    def __call__(self, url: str) -> Union[str, bytes]:
        """
        Process a transcript URL and return the content.
        
        Args:
            url: The URL to process
            
        Returns:
            Processed content as string or bytes
            
        Raises:
            Any exception that occurs during processing
        """
        ...

class VideoLinkExtractor(Protocol):
    """Protocol defining the interface for video link extraction functions."""
    def __call__(self, url: str) -> Tuple[str, str]:
        """
        Process a video page URL and return the actual downloadable link and its type.
        
        Args:
            url: The URL to process
            
        Returns:
            Tuple[str, str]: (downloadable_url, link_type)
            where link_type is one of: 'mp4_video_link', 'm3u8_link', etc.
            matching the keys in DOWNLOAD_FUNCTIONS
            
        Raises:
            Any exception that occurs during processing
        """
        ...

def download_and_process_with_link_extractor(
    url: str,
    output_filename: str,
    extractor: VideoLinkExtractor,
    download_functions: Dict[str, Any]
) -> bool:
    """
    Extract downloadable link using custom extractor and process with appropriate downloader.
    
    Args:
        url: Source URL to process
        output_filename: Where to save the processed file
        extractor: Function that processes the URL and returns downloadable link
        download_functions: Dictionary mapping link types to download functions
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract the actual downloadable link and its type
        logging.info(f"Extracting downloadable link from: {url}")
        downloadable_url, link_type = extractor(url)
        
        # Validate the link type
        if link_type not in download_functions:
            raise ValueError(f"Unsupported link type returned by extractor: {link_type}")
            
        # Get the appropriate download function
        download_func = download_functions[link_type]
        
        logging.info(f"Extracted {link_type} link: {downloadable_url}")
        
        # Download using the existing function
        return download_func(downloadable_url, output_filename)
        
    except Exception as e:
        logging.error(f"Error processing {url} with link extractor: {str(e)}")
        return False

def download_and_process_with_custom_processor(
    url: str, 
    output_filename: str,
    processor: TranscriptProcessor,
    file_extension: str,
    batch_storage=False,
    update_frequency=10,
    start_idx=0,
    end_idx=0
) -> bool:
    """
    Download and process content using a custom processor function.
    
    Args:
        url: Source URL to process
        output_filename: Base filename for output (without extension)
        processor: Function that processes the URL and returns content
        file_extension: Extension for the output file (e.g., 'html', 'txt')
        batch_storage: Whether to use batch storage
        update_frequency: How often to update the batch file
        start_idx: Starting row index for this process
        end_idx: Ending row index for this process
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Initialize temp_dir to None before any code paths
    temp_dir = None
    
    try:
        # Extract transcript ID from the output filename
        transcript_id = os.path.basename(output_filename)
        
        # Get the subfolder path
        subfolder_path = os.path.dirname(output_filename)
        
        if batch_storage and BatchStorageManager is not None:
            # Get batch storage manager for this subfolder
            batch_manager = BatchStorageManager.get_instance(
                subfolder_path, start_idx, end_idx, update_frequency
            )
            
            # Check if transcript already exists in batch storage
            existing_content = batch_manager.get_transcript(transcript_id)
            if existing_content:
                logging.info(f"Transcript {transcript_id} already exists in batch storage")
                return True
            
            # Process content using provided processor
            content = processor(url)
            
            # Add to batch storage
            metadata = {
                "original_url": url,
                "file_extension": file_extension,
                "processed_at": datetime.now().isoformat()
            }
            
            success = batch_manager.add_transcript(
                transcript_id=transcript_id,
                content=content,
                url=url,
                metadata=metadata
            )
            
            if success:
                logging.info(f"Added transcript {transcript_id} to batch storage")
                return True
            else:
                logging.error(f"Failed to add transcript {transcript_id} to batch storage")
                return False
        else:
            # Original individual file storage logic
            # Create temp directory
            base_dir = os.path.dirname(os.path.dirname(__file__))
            temp_dir = os.path.join(base_dir, f'temp_downloaded_{file_extension}')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Setup paths
            temp_file = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.{file_extension}')
            final_file = f'{output_filename}.{file_extension}'
            
            # Process content
            content = processor(url)
            
            # Save to temp file
            mode = 'wb' if isinstance(content, bytes) else 'w'
            encoding = None if isinstance(content, bytes) else 'utf-8'
            with open(temp_file, mode, encoding=encoding) as f:
                f.write(content)
            
            # Move to final location
            shutil.move(temp_file, final_file)
            logging.info(f"Successfully processed: {url}")
            
            return True
        
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return False
    finally:
        # Check if temp_dir exists and is not None before trying to clean it up
        if temp_dir and os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

# Map local modalities to Supabase modalities
SUPABASE_MODALITY_MAPPING = {
    'audio': 'video',      # All audio/video content maps to video in Supabase
    'subtitle': 'video',   # Subtitles are associated with videos
    'transcript': 'transcript'  # Transcripts map directly
}

def add_download_delay():
    """
    Add a random delay between downloads to avoid overwhelming the server.
    The delay is between 8-12 seconds normally, with occasional
    longer delays (15-20 seconds) to simulate more natural behavior.
    This gives us a mean delay of about 10 seconds, with some variation
    to make the behavior look more natural.
    """
    if random.random() < 0.1:  # 10% chance of a longer delay
        delay = random.uniform(15, 20)
    else:
        delay = random.uniform(8, 12)
    time.sleep(delay)

def get_video_duration(file_path: str) -> int:
    """
    Get video duration in seconds using ffprobe.
    Returns 0 if duration cannot be determined.
    """
    try:
        # Append .opus extension if not present
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
    """
    Get file size in bytes.
    Returns 0 if size cannot be determined.
    """
    try:
        # Append .opus extension if not present
        if not file_path.endswith('.opus'):
            file_path = f"{file_path}.opus"
            
        return os.path.getsize(file_path)
    except Exception as e:
        logging.error(f"Failed to get file size: {str(e)}")
        return 0

def with_retry(func, args, column_info, session_id):
    """
    Generic retry wrapper that handles both patterns:
    - Functions returning False/True
    - Functions returning error string/True
    
    Maintains original retry logic with wait times and adds Supabase tracking.
    """
    wait_times = [120, 240, 480, 960]  # 2, 4, 8, 16 minutes in seconds
    modality = column_info['modality']
    
    # Map local modality to Supabase modality
    supabase_modality = SUPABASE_MODALITY_MAPPING[modality]
    
    # Start download tracking
    start_download(session_id, supabase_modality)
    
    for attempt, wait_time in enumerate(wait_times, 1):
        try:
            result = func(*args)
            
            if result is False:
                # Get the last logged error message from the logging handler
                error_msg = f"Download failed for {args}"
                logging.warning(f"Attempt {attempt} failed: {error_msg}")
            elif isinstance(result, str):
                error_msg = result
                logging.warning(f"Attempt {attempt} failed: {error_msg}")
                if "HTTP Error 404" in error_msg:
                    fail_download(session_id, supabase_modality, error_msg, retry_count=attempt)
                    logging.error(f"All attempts failed for {args} after {len(wait_times)} tries.")
                    return False
            else:
                # Success case
                metrics = None
                if modality == 'audio':  # Only collect metrics for audio files
                    output_path = args[1]
                    metrics = {
                        'duration': get_video_duration(output_path),
                        'size': get_file_size(output_path)
                    }
                complete_download(session_id, supabase_modality, metrics)
                return True
                
            # Handle retry for both False and string error cases
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
                continue
            else:
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
                # Final failure - update Supabase and raise
                fail_download(session_id, supabase_modality, error_msg, retry_count=attempt)
                logging.error(f"All attempts failed for {args} after {len(wait_times)} tries.")
                raise e
    
    return False

def get_transcript_id(transcript_link):
    """Extract the date/time identifier from transcript link."""
    return transcript_link.split('/')[-1]

def get_youtube_id(youtube_url):
    """Extract video ID from YouTube URL."""
    # Match patterns like v=XXXXX or /v/XXXXX
    pattern = r'(?:v=|/v/|youtu\.be/)([^&\n?#]+)'
    match = re.search(pattern, youtube_url)
    return match.group(1) if match else None

def get_bundestag_video_id(url):

    """
    Extract video ID from Bundestag media URL.
    
    Args:
        url: Full URL from Bundestag mediathek
        
    Returns:
        Video ID as string, or None if not found
    """
    try:
        # Split on 'videoid=' and take the part after
        video_id = url.split('videoid=')[1]
        
        # If there's a '#' or any other characters after the ID, remove them
        if '#' in video_id:
            video_id = video_id.split('#')[0]
            
        return video_id
    except Exception:
        return None



# Download and process audio links
def download_and_process_mp4_video(mp4_link: str, output_filename: str) -> bool:
    """
    Download MP4 and convert to opus audio format.
    
    Args:
        mp4_link: Direct link to MP4 file
        output_filename: Desired output filename (without extension)
    """
    try:
        # Create temp directory in parent folder (Germany/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_opus = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.opus')
        final_opus = f'{output_filename}.opus'

        # Download and extract audio directly with ffmpeg
        download_command = [
            'ffmpeg',
            '-i', mp4_link,
            '-vn',               # No video
            '-c:a', 'libopus',   # Opus codec
            '-b:a', '96k',       # 96 kbps bitrate
            '-ac', '1',          # Mono
            '-ar', '24000',      # 24kHz
            '-application', 'voip',  # Optimize for speech
            temp_opus
        ]
        
        # Download and convert in one step
        logging.info(f"Starting download for: {mp4_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_opus, final_opus)
        logging.info(f"Successfully processed: {mp4_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {mp4_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def download_and_process_youtube(youtube_url, output_filename):

    """Download audio and convert to target format."""
    try:
        # First, download best audio quality available
        download_command = [
            'yt-dlp',
            '-f', 'bestaudio',  # Get best audio
            '--extract-audio',
            '--audio-format', 'opus',  # Keep as opus initially
            '-o', f'temp_{output_filename}.%(ext)s',
            youtube_url
        ]
        
        subprocess.run(download_command, check=True, capture_output=True)
        
        # Load the downloaded audio file
        temp_filename = f'temp_{output_filename}.opus'
        temp_dir = 'temp_downloaded_audio'

        
        # Convert to target format using ffmpeg directly
        temp_file = next(f for f in os.listdir(temp_dir) if f.startswith(os.path.basename(output_filename)))
        temp_file = os.path.join(temp_dir, temp_file)

        convert_command = [
            'ffmpeg',
            '-i', temp_file,
            '-c:a', 'libopus',        # Opus codec
            '-b:a', '96k',            # 96 kbps bitrate
            '-ac', '1',               # Mono
            '-ar', '24000',           # 24kHz
            '-application', 'voip',   # Optimize for speech
            f'{output_filename}.opus'
        ]

        subprocess.run(convert_command, check=True, capture_output=True)
        
        # Remove temporary file
        os.remove(temp_filename)
        
        return True
    except Exception as e:
        print(f"Error processing {youtube_url}: {str(e)}")
        return False

def download_and_process_m3u8_video(url: str, output_filename: str) -> bool:
    """
    Download m3u8 stream and convert to opus audio format.
    
    Args:
        url: URL to the webpage or direct m3u8 URL
        output_filename: Desired output filename (without extension)
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_opus = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.opus')
        final_opus = f'{output_filename}.opus'

        # Use ffmpeg directly with m3u8 input
        download_command = [
            'ffmpeg',
            '-i', url,
            '-vn',               # No video
            '-c:a', 'libopus',   # Opus codec
            '-b:a', '96k',       # 96 kbps bitrate
            '-ac', '1',          # Mono
            '-ar', '24000',      # 24kHz
            '-application', 'voip',  # Optimize for speech
            temp_opus
        ]
        
        # Download and convert in one step
        logging.info(f"Starting download for: {url}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_opus, final_opus)
        logging.info(f"Successfully processed: {url}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def download_and_process_generic_video(url: str, output_filename: str) -> bool:
    """
    Download video from generic video players using yt-dlp and convert to opus audio format.
    Used when direct media links are not available and video must be extracted from a web player.
    
    Args:
        url: URL of the video player page
        output_filename: Desired output filename (without extension)
    """
    try:
        add_download_delay()  # Add delay before download
        # Create temp directory in parent folder
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_opus = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.opus')
        final_opus = f'{output_filename}.opus'

        # yt-dlp command with direct audio extraction and proxy settings
        download_command = [
            'yt-dlp',
            #'--proxy', PROXY_URL,  # Add proxy
            '-x',  # Extract audio
            '--audio-format', 'opus',  # Convert to opus
            '--audio-quality', '96k',  # 96 kbps
            '--retries', '20',  # Increased retries
            '--fragment-retries', '20',  # Added fragment retries
            '--postprocessor-args', '-ac 1 -ar 24000 -application voip',  # Your ffmpeg settings
            '-o', temp_opus,
            url
        ]
        
        # Download and convert in one step
        logging.info(f"Starting download for: {url}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"yt-dlp error: {result.stderr}")
            return f"yt-dlp error: {result.stderr}"
        
        # Move to final location
        shutil.move(temp_opus, final_opus)
        logging.info(f"Successfully processed: {url}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return f"Error processing {url}: {str(e)}"
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

# Download and process transcript links
def download_and_process_html(html_link: str, output_filename: str) -> bool:
    """
    Download HTML file.
    """
    try:
        add_download_delay()  # Add delay before download
        # Create temp directory in parent folder (Germany/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_html')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_html = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.html')
        final_html = f'{output_filename}.html'

        # Download HTML file using curl
        download_command = [
            'curl',
            '-L',  # Follow redirects
            '-o', temp_html,  # Output file
            html_link
        ]
        
        logging.info(f"Starting download for: {html_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Curl error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_html, final_html)
        logging.info(f"Successfully processed: {html_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {html_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

    """
    Download SRT subtitle file.
    """
    try:
        # Create temp directory in parent folder (Germany/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_subtitle')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_srt = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.srt')
        final_srt = f'{output_filename}.srt'

        # Download SRT file using curl
        download_command = [
            'curl',
            '-L',  # Follow redirects
            '-o', temp_srt,  # Output file
            srt_link
        ]
        
        logging.info(f"Starting download for: {srt_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Curl error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_srt, final_srt)
        logging.info(f"Successfully processed: {srt_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {srt_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def download_and_process_pdf(pdf_link: str, output_filename: str, redownload_transcripts: bool = True) -> bool:
    """
    Download PDF transcript file using curl_cffi to bypass protections.
    
    Args:
        pdf_link: Direct link to PDF file
        output_filename: Desired output filename (without extension)
        redownload_transcripts: Whether to redownload even if exists
    """
    try:
        # Import curl_cffi here to avoid dependency issues if not installed
        from curl_cffi import requests as curl_requests
        
        # Create temp directory
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_transcript')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_pdf = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.pdf')
        final_pdf = f'{output_filename}.pdf'
        
        # Check if file already exists
        if os.path.exists(final_pdf) and not redownload_transcripts:
            logging.info(f"PDF file {final_pdf} already exists and redownload not requested")
            return True

        # Set headers to look more like a real browser
        headers = {
            "Referer": pdf_link.split('/')[0] if '/' in pdf_link else pdf_link,
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        
        # Try multiple browser impersonations in case one fails
        browser_types = ["chrome110", "chrome107", "safari15_3", "firefox91"]
        download_success = False
        
        for browser in browser_types:
            try:
                logging.info(f"Trying to download {pdf_link} with {browser} impersonation...")
                
                # Make request with browser impersonation
                response = curl_requests.get(
                    pdf_link, 
                    impersonate=browser,
                    headers=headers,
                    timeout=30
                )
                
                # Check if request was successful and content is PDF
                if response.status_code == 200 and response.headers.get('content-type', '').lower().startswith('application/pdf'):
                    # Save the file
                    with open(temp_pdf, "wb") as f:
                        f.write(response.content)
                    
                    logging.info(f"Successfully downloaded using {browser} impersonation")
                    download_success = True
                    break
                else:
                    logging.warning(f"Failed with {browser}: HTTP {response.status_code}, Content-Type: {response.headers.get('content-type')}")
            
            except Exception as e:
                logging.warning(f"Error with {browser}: {str(e)}")
        
        if not download_success:
            logging.error(f"All browser impersonations failed for {pdf_link}")
            return False
            
        # Move to final location
        shutil.move(temp_pdf, final_pdf)
        logging.info(f"Successfully processed: {pdf_link}")
        
        return True
        
    except ImportError:
        logging.error("curl_cffi not installed. Please install with: pip install curl_cffi")
        return False
    except Exception as e:
        logging.error(f"Error processing {pdf_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)


# Download and process subtitle links
def download_and_process_srt(srt_link: str, output_filename: str) -> bool:
    """
    Download SRT subtitle file.
    """
    try:
        # Create temp directory in parent folder (Germany/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_subtitle')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_srt = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.srt')
        final_srt = f'{output_filename}.srt'

        # Download SRT file using curl
        download_command = [
            'curl',
            '-L',  # Follow redirects
            '-o', temp_srt,  # Output file
            srt_link
        ]
        
        logging.info(f"Starting download for: {srt_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Curl error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_srt, final_srt)
        logging.info(f"Successfully processed: {srt_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {srt_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def get_video_url(url: str, patterns: List[str]) -> Optional[str]:
    """
    Extract m3u8 URL from a webpage using a list of regex patterns.
    
    Args:
        url: URL of the webpage containing the video
        patterns: List of regex patterns to try
    
    Returns:
        str: The extracted m3u8 URL if found, None otherwise
    """
    response = None
    try:
        # Initial GET request with proxy
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, proxies=PROXY_CONFIG)
        
        for pattern in patterns:
            if matches := re.findall(pattern, response.text, re.IGNORECASE):
                url_to_test = matches[0] if isinstance(matches[0], str) else matches[0][0]
                
                # Add a small delay before the HEAD request
                time.sleep(random.uniform(1, 2))  # Random delay between 1-2 seconds
                
                if requests.head(url_to_test, timeout=5, proxies=PROXY_CONFIG).status_code == 200:
                    return url_to_test
                
                # Add a small delay between pattern attempts if the HEAD request fails
                time.sleep(random.uniform(0.5, 1))
                
        # If we get here, no pattern matched
        if response:
            logging.error(f"Page source: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error extracting video URL: {str(e)}")
        if response:
            logging.error(f"Page source: {response.text}")
        return None

def download_and_process_generic_m3u8_link(url: str, output_filename: str) -> bool:
    """
    Extract m3u8 URL from a webpage and download it.
    This function is specifically designed for pages like the Croatian parliament
    that embed m3u8 streams.
    
    Args:
        url: URL of the webpage containing the video
        output_filename: Desired output filename (without extension)
    """
    # Patterns to find m3u8 URLs in the page source
    patterns = [
        r'(https?://[^\s<>"]+?/vod/_definst_/(?:mpflv):[^\s<>"]+?\.(?:mp4|m3u8))',
        r'(https?://[^\s<>"]+?/(?:playlist|manifest)\.(?:m3u8|mpd))',
        r'(https?://[^\s<>"]+?\.(?:m3u8|mpd)(?:\?[^\s<>"]*)?)',
        r'streamUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
        r'videoUrl[\s]*[=:][\s]*[\'"]([^\'"]+)[\'"]',
        r'(https?://[^\s<>"]+?/\d{4}/\d{2}/\d{2}/[^\s<>"]+?\.(?:mp4|m3u8))'
    ]
    
    # Extract the m3u8 URL
    m3u8_url = get_video_url(url, patterns)
    if not m3u8_url:
        logging.error(f"Could not find m3u8 URL in page: {url}")
        logging.error(f"Page source: {response.text}")    
        return False
    
    logging.info(f"Found m3u8 URL: {m3u8_url}")
    
    # Store the mapping in a CSV file
    base_dir = os.path.dirname(os.path.dirname(__file__))
    csv_file = os.path.join(base_dir, 'extracted_m3u8_links.csv')
    
    # Create CSV file with headers if it doesn't exist
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['original_url', 'm3u8_url', 'video_id', 'timestamp'])
    
    # Append the new mapping
    video_id = os.path.basename(output_filename)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([url, m3u8_url, video_id, timestamp])
    
    # Use the existing m3u8 download function
    return download_and_process_m3u8_video(m3u8_url, output_filename)

def download_and_process_dynamic_html(html_link: str, output_filename: str) -> bool:
    """
    Download HTML file using Playwright to handle dynamically loaded content.
    This function waits for the page to be fully loaded before saving the content.
    """
    try:
        add_download_delay()  # Add delay before download
        # Create temp directory in parent folder
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_dynamic_html')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_html = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.html')
        final_html = f'{output_filename}.html'

        # Use Playwright to get the fully rendered page
        with sync_playwright() as p:
            browser = p.chromium.launch(proxy={
                "server": f"http://168.151.206.16:20000",
                "username": "island",
                "password": "ausgeTrickst=)"
            })
            page = browser.new_page()
            
            # Navigate and wait for network idle
            page.goto(html_link, wait_until='networkidle')
            
            # Wait additional time for any dynamic content
            page.wait_for_timeout(2000)  # 2 seconds
            
            # Get the full HTML content
            content = page.content()
            
            # Save to temp file
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(content)
            
            browser.close()
        
        # Move to final location
        shutil.move(temp_html, final_html)
        logging.info(f"Successfully processed dynamic HTML: {html_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing dynamic HTML {html_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def download_and_process_doc(doc_link: str, output_filename: str, redownload_transcripts: bool = True) -> bool:
    """
    Download Word document files (.doc or .docx) using curl_cffi to bypass protections.
    
    Args:
        doc_link: Direct link to Word document
        output_filename: Desired output filename (without extension)
        redownload_transcripts: Whether to redownload even if exists
    """
    try:
        # Import curl_cffi here to avoid dependency issues if not installed
        from curl_cffi import requests as curl_requests
        
        # Create temp directory
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_transcript')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Determine file extension from URL
        ext = '.docx' if doc_link.lower().endswith('.docx') else '.doc'
        
        # Setup temporary and final paths
        temp_doc = os.path.join(temp_dir, f'{os.path.basename(output_filename)}{ext}')
        final_doc = f'{output_filename}{ext}'
        
        # Check if file already exists
        if os.path.exists(final_doc) and not redownload_transcripts:
            logging.info(f"Document file {final_doc} already exists and redownload not requested")
            return True

        # Set headers to look more like a real browser
        headers = {
            "Referer": doc_link.split('/')[0] if '/' in doc_link else doc_link,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        
        # Try multiple browser impersonations in case one fails
        browser_types = ["chrome110", "chrome107", "safari15_3", "firefox91"]
        download_success = False
        
        for browser in browser_types:
            try:
                logging.info(f"Trying to download {doc_link} with {browser} impersonation via proxy...")
                
                # Make request with browser impersonation and proxy
                response = curl_requests.get(
                    doc_link, 
                    impersonate=browser,
                    headers=headers,
                    timeout=30
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    # Save the file
                    with open(temp_doc, "wb") as f:
                        f.write(response.content)
                    
                    logging.info(f"Successfully downloaded using {browser} impersonation with proxy")
                    download_success = True
                    break
                else:
                    logging.warning(f"Failed with {browser} via proxy: HTTP {response.status_code}")
            
            except Exception as e:
                logging.warning(f"Error with {browser} via proxy: {str(e)}")
        
        if not download_success:
            logging.error(f"All browser impersonations failed for {doc_link} using proxy")
            return False
            
        # Move to final location
        shutil.move(temp_doc, final_doc)
        logging.info(f"Successfully processed: {doc_link}")
        
        return True
        
    except ImportError:
        logging.error("curl_cffi not installed. Please install with: pip install curl_cffi")
        return False
    except Exception as e:
        logging.error(f"Error processing {doc_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
def download_and_process_mp3(mp3_link: str, output_filename: str) -> bool:
    """
    Download MP3 audio file and convert to opus format.
    Uses curl_cffi to bypass Cloudflare and other protections.
    
    Args:
        mp3_link: Direct link to MP3 file
        output_filename: Desired output filename (without extension)
    """
    try:
        # Import curl_cffi here to avoid dependency issues if not installed
        from curl_cffi import requests as curl_requests
        from urllib.parse import unquote
        
        # Create temp directory
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_mp3 = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.mp3')
        temp_opus = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.opus')
        final_opus = f'{output_filename}.opus'

        # Set headers to look more like a real browser
        headers = {
            "Referer": mp3_link.split('/Audio/')[0] if '/Audio/' in mp3_link else '/'.join(mp3_link.split('/')[0:3]),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        
        # Try multiple browser impersonations in case one fails
        browser_types = ["chrome110", "chrome107", "safari15_3", "firefox91"]
        download_success = False
        
        for browser in browser_types:
            try:
                logging.info(f"Trying to download {mp3_link} with {browser} impersonation...")
                
                # Make request with browser impersonation
                response = curl_requests.get(
                    mp3_link, 
                    impersonate=browser,
                    headers=headers,
                    timeout=30
                )
                
                # Check if request was successful
                if response.status_code == 200:
                    # Save the file
                    with open(temp_mp3, "wb") as f:
                        f.write(response.content)
                    
                    logging.info(f"Successfully downloaded using {browser} impersonation")
                    download_success = True
                    break
                else:
                    logging.warning(f"Failed with {browser}: HTTP {response.status_code}")
            
            except Exception as e:
                logging.warning(f"Error with {browser}: {str(e)}")
        
        if not download_success:
            logging.error(f"All browser impersonations failed for {mp3_link}")
            return False
            
        # Convert MP3 to opus using ffmpeg
        convert_command = [
            'ffmpeg',
            '-i', temp_mp3,
            '-c:a', 'libopus',   # Opus codec
            '-b:a', '96k',       # 96 kbps bitrate
            '-ac', '1',          # Mono
            '-ar', '24000',      # 24kHz
            '-application', 'voip',  # Optimize for speech
            temp_opus
        ]
        
        logging.info(f"Converting MP3 to opus format")
        result = subprocess.run(convert_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_opus, final_opus)
        
        # Remove temporary MP3 file
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
            
        logging.info(f"Successfully processed: {mp3_link}")
        
        return True
        
    except ImportError:
        logging.error("curl_cffi not installed. Please install with: pip install curl_cffi")
        return False
    except Exception as e:
        logging.error(f"Error processing {mp3_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

