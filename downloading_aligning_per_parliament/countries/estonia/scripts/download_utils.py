import pandas as pd
import subprocess
import os
from tqdm import tqdm
import re



import time
import logging

def download_and_process_with_retry(youtube_link, output_filename):
    wait_times = [120, 240, 480, 960]  # 2, 4, 8, 16 minutes in seconds
    
    for attempt, wait_time in enumerate(wait_times, 1):
        try:
            return download_and_process_audio(youtube_link, output_filename)
        except Exception as e:
            if attempt < len(wait_times):
                minutes = wait_time // 60
                logging.warning(f"Attempt {attempt} failed for {youtube_link}: {str(e)}. Waiting {minutes} minutes before retry...")
                time.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for {youtube_link} after {len(wait_times)} tries.")
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

