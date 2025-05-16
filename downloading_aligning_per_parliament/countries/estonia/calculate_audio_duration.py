#!/usr/bin/env python3
import os
import sys
from mutagen.oggopus import OggOpus
from datetime import timedelta
import time

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    return str(timedelta(seconds=int(seconds)))

def get_audio_duration(file_path):
    """Get the duration of an audio file in seconds"""
    try:
        audio = OggOpus(file_path)
        return audio.info.length
    except Exception as e:
        print(f"Error reading {os.path.basename(file_path)}: {e}")
        return 0

def main():
    # Get the folder path from command line arguments or use default
    folder_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # Get all opus files
    opus_files = [f for f in os.listdir(folder_path) if f.endswith('.opus')]
    total_files = len(opus_files)
    
    if total_files == 0:
        print("No .opus files found in the directory.")
        return
    
    print(f"Found {total_files} opus files. Starting duration calculation...")
    print("-" * 60)
    
    # Process each file and accumulate duration
    total_duration = 0
    for index, filename in enumerate(opus_files, 1):
        file_path = os.path.join(folder_path, filename)
        
        # Get file size in MB
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # Get duration
        start_time = time.time()
        duration = get_audio_duration(file_path)
        process_time = time.time() - start_time
        
        # Add to total
        total_duration += duration
        
        # Progress output
        progress = (index / total_files) * 100
        total_hours = total_duration / 3600
        
        print(f"[{index}/{total_files}] {progress:.1f}% - {filename}")
        print(f"  Size: {file_size_mb:.2f} MB | Duration: {format_time(duration)}")
        print(f"  Accumulated duration: {format_time(total_duration)} ({total_hours:.2f} hours)")
        print("-" * 60)
    
    # Final summary
    print("\nSummary:")
    print(f"Total number of files: {total_files}")
    print(f"Total duration: {format_time(total_duration)} ({total_duration/3600:.2f} hours)")

if __name__ == "__main__":
    main() 