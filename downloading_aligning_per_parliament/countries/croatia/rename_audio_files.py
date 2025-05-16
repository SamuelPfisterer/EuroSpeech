import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm

def rename_audio_files():
    """Rename transcript_id.opus files to video_id.opus if needed."""
    
    # Load the final CSV with video_ids and transcript_ids
    final_df = pd.read_csv('croatian_parliament_media_links_final.csv')
    
    # Check if the required columns exist
    if 'video_id' not in final_df.columns or 'transcript_id' not in final_df.columns:
        print("Error: CSV must contain both video_id and transcript_id columns")
        return
    
    # Path to audio files directory
    audio_dir = Path('downloaded_audio/m3u8_streams')
    
    if not audio_dir.exists():
        print(f"Error: Directory {audio_dir} doesn't exist")
        return
    
    # Filter rows that have both video_id and transcript_id
    valid_rows = final_df.dropna(subset=['video_id', 'transcript_id'])
    print(f"Found {len(valid_rows)} rows with both video_id and transcript_id")
    
    # Counters for tracking
    renamed_count = 0
    already_exists_count = 0
    missing_transcript_file_count = 0
    error_count = 0
    
    # Process each row
    for _, row in tqdm(valid_rows.iterrows(), total=len(valid_rows), desc="Renaming files"):
        video_id = str(row['video_id'])
        transcript_id = str(row['transcript_id'])
        
        video_file = audio_dir / f"{video_id}.opus"
        transcript_file = audio_dir / f"{transcript_id}.opus"
        
        # Check if video_id.opus already exists
        if video_file.exists():
            already_exists_count += 1
            continue
        
        # Check if transcript_id.opus exists
        if not transcript_file.exists():
            missing_transcript_file_count += 1
            continue
        
        # Rename the file
        try:
            transcript_file.rename(video_file)
            renamed_count += 1
            
            # Print progress every 100 files
            if renamed_count % 100 == 0:
                print(f"Renamed {renamed_count} files so far...")
                
        except Exception as e:
            print(f"Error renaming {transcript_file} to {video_file}: {e}")
            error_count += 1
    
    # Print summary
    print("\nRenaming Summary:")
    print(f"Total files renamed: {renamed_count}")
    print(f"Files already named with video_id: {already_exists_count}")
    print(f"Missing transcript files: {missing_transcript_file_count}")
    print(f"Errors during renaming: {error_count}")
    
    # Create a report file
    with open('audio_renaming_report.txt', 'w') as f:
        f.write("Audio File Renaming Report\n")
        f.write("=========================\n\n")
        f.write(f"Total rows processed: {len(valid_rows)}\n")
        f.write(f"Total files renamed: {renamed_count}\n")
        f.write(f"Files already named with video_id: {already_exists_count}\n")
        f.write(f"Missing transcript files: {missing_transcript_file_count}\n")
        f.write(f"Errors during renaming: {error_count}\n")
    
    print(f"Report saved to audio_renaming_report.txt")

if __name__ == "__main__":
    rename_audio_files()
