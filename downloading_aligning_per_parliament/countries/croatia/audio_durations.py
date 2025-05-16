import os
import csv
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import subprocess

def get_audio_duration(file_path):
    """Get the duration of an audio file using ffprobe."""
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

def main():
    base_dir = Path("downloaded_audio/m3u8_streams")
    output_csv = "audio_durations.csv"
    
    # Load the final CSV to get video_ids
    try:
        final_df = pd.read_csv('croatian_parliament_media_links_final.csv')
        video_ids = final_df['video_id'].dropna().unique().tolist()
        print(f"Found {len(video_ids)} unique video_ids in the final CSV")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        print("Continuing with all .opus files in the directory")
        video_ids = []
    
    # Find all video_id.opus files
    opus_files = []
    
    if video_ids:
        # If we have video_ids, look specifically for those files
        for video_id in video_ids:
            file_path = base_dir / f"{video_id}.opus"
            if file_path.exists():
                opus_files.append(str(file_path))
        print(f"Found {len(opus_files)} matching video_id.opus files")
    else:
        # Fallback to all .opus files
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.opus'):
                    opus_files.append(os.path.join(root, file))
        print(f"Found {len(opus_files)} total .opus files")
    
    # Process files with tqdm
    durations = []
    total_duration_seconds = 0
    
    with open(output_csv, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Video ID', 'Duration (hours)'])
        
        for file_path in tqdm(opus_files, desc="Processing audio files"):
            try:
                duration_seconds = get_audio_duration(file_path)
                duration_hours = duration_seconds / 3600
                
                # Extract video_id from filename
                video_id = Path(file_path).stem
                
                total_duration_seconds += duration_seconds
                durations.append((video_id, duration_hours))
                
                csv_writer.writerow([video_id, duration_hours])
                
                # Print intermediate progress every 10 files to avoid too much output
                if len(durations) % 10 == 0:
                    total_hours = total_duration_seconds / 3600
                    print(f"Processed {len(durations)} files")
                    print(f"Latest file: {file_path}")
                    print(f"Accumulated duration: {total_hours:.2f} hours")
                    print("-" * 30)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    # Print final summary
    total_hours = total_duration_seconds / 3600
    print(f"\nTotal audio duration: {total_hours:.2f} hours")
    print(f"Total files processed: {len(durations)}")
    print(f"Average file duration: {(total_hours / len(durations) if durations else 0):.2f} hours")
    print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    main()
