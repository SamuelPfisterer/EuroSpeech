import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re
import shutil



import time
import logging

def with_retry(processing_function, *args):
    """
    Generic retry wrapper for any download and process function.
    
    Args:
        processing_function: The function to execute with retry logic
        *args: Arguments to pass to the processing function
    """
    wait_times = [120, 240, 480, 960]  # 2, 4, 8, 16 minutes in seconds
    
    for attempt, wait_time in enumerate(wait_times, 1):
        try:
            return processing_function(*args)
        except Exception as e:
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Attempt {attempt} failed for {args}: {str(e)}. Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for {args} after {len(wait_times)} tries.")
                raise e

def download_and_process_video_with_retry(mp4_link, output_filename):
    wait_times = [120, 240, 480, 960]  # 2, 4, 8, 16 minutes in seconds
    
    for attempt, wait_time in enumerate(wait_times, 1):
        try:
            return download_and_process_mp4_video(mp4_link, output_filename)
        except Exception as e:
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Video download attempt {attempt} failed for {mp4_link}: {str(e)}. Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for {mp4_link} after {len(wait_times)} tries.")
                raise e

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

def download_and_process_audio(youtube_url, output_filename):

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

def download_and_process_pdf(pdf_link: str, output_filename: str) -> bool:
    """
    Download PDF transcript file.
    """
    try:
        # Create temp directory in parent folder (Germany/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        temp_dir = os.path.join(base_dir, 'temp_downloaded_transcript')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup temporary and final paths
        temp_pdf = os.path.join(temp_dir, f'{os.path.basename(output_filename)}.pdf')
        final_pdf = f'{output_filename}.pdf'

        # Download PDF file using curl
        download_command = [
            'curl',
            '-L',  # Follow redirects
            '-o', temp_pdf,  # Output file
            pdf_link
        ]
        
        logging.info(f"Starting download for: {pdf_link}")
        result = subprocess.run(download_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f"Curl error: {result.stderr}")
            return False
        
        # Move to final location
        shutil.move(temp_pdf, final_pdf)
        logging.info(f"Successfully processed: {pdf_link}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {pdf_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    """
    Download PDF transcript file.
    
    Args:
        pdf_link: Direct link to PDF file
        output_filename: Desired output filename (without extension)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        os.makedirs('temp_downloaded_transcript', exist_ok=True)
        temp_dir = 'temp_downloaded_transcript'
        temp_pdf = os.path.join(temp_dir, f'temp_{output_filename}.pdf')
        final_pdf = f'{output_filename}.pdf'

        # Download PDF file using curl or wget
        download_command = [
            'curl',
            '-L',  # Follow redirects
            '-o', temp_pdf,  # Output file
            pdf_link
        ]
        # Alternative using wget:
        # download_command = ['wget', '-O', temp_pdf, pdf_link]
        
        # Download file
        subprocess.run(download_command, check=True, capture_output=True)
        
        # Move to final location
        shutil.move(temp_pdf, final_pdf)
        
        return True
        
    except Exception as e:
        print(f"Error processing {pdf_link}: {str(e)}")
        return False
    finally:
        # Cleanup temp directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)