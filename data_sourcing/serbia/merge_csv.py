import csv
import re
from typing import List, Dict, Tuple
import pandas as pd

def extract_date_from_id(id_str: str) -> str:
    """
    Extract the date portion from an ID string (transcript_id or video_id).
    IDs are expected to be in format: serbia_{convocation}_{index}_{date}
    
    Args:
        id_str: The ID string to parse
        
    Returns:
        The date string in ddmmyyyy format or None if no date is found
    """
    # Use regex to extract the date part (last component after underscores)
    return id_str.split('_')[-1]

def merge_csvs(transcript_csv_path: str, video_csv_path: str, output_csv_path: str) -> None:
    """
    Merge transcript and video CSVs based on matching dates.
    Creates all possible combinations (n*m) when multiple rows share the same date.
    Excludes rows with dates that don't appear in both CSVs.
    
    Args:
        transcript_csv_path: Path to the transcript CSV file
        video_csv_path: Path to the video CSV file
        output_csv_path: Path to save the merged CSV file
    """
    try:
        # Load transcript data
        transcript_data = []
        with open(transcript_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = extract_date_from_id(row['transcript_id'])
                if date:
                    row['date'] = date
                    transcript_data.append(row)
                else:
                    print(f"Warning: Could not extract date from transcript_id: {row['transcript_id']}")
        
        # Load video data
        video_data = []
        with open(video_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = extract_date_from_id(row['video_id'])
                if date:
                    row['date'] = date
                    video_data.append(row)
                else:
                    print(f"Warning: Could not extract date from video_id: {row['video_id']}")
        
        print(f"Loaded {len(transcript_data)} transcript rows and {len(video_data)} video rows")
        
        # Convert to pandas DataFrames for easier joining
        transcript_df = pd.DataFrame(transcript_data)
        video_df = pd.DataFrame(video_data)
        
        # Rename title columns before merging to avoid automatic suffixes
        transcript_df = transcript_df.rename(columns={'title': 'transcript_title'})
        video_df = video_df.rename(columns={'title': 'video_title'})
        
        # Create merged dataframe with all combinations for matching dates
        merged_df = pd.merge(
            transcript_df, 
            video_df, 
            on='date', 
            how='inner'  # inner join keeps only rows with matching dates in both dataframes
        )
        
        # Summary statistics
        print(f"Unique dates in transcript data: {transcript_df['date'].nunique()}")
        print(f"Unique dates in video data: {video_df['date'].nunique()}")
        print(f"Unique dates in merged data: {merged_df['date'].nunique()}")
        print(f"Total rows in merged data: {len(merged_df)}")
        
        # Additional columns if needed
        merged_df['merged_id'] = merged_df['transcript_id'] + '_' + merged_df['video_id']
        
        # Save to CSV
        merged_df.to_csv(output_csv_path, index=False)
        print(f"Merged data saved to {output_csv_path}")
        
        # Report unmatched dates
        transcript_dates = set(transcript_df['date'])
        video_dates = set(video_df['date'])
        
        unmatched_transcript_dates = transcript_dates - video_dates
        unmatched_video_dates = video_dates - transcript_dates
        
        if unmatched_transcript_dates:
            print(f"Warning: {len(unmatched_transcript_dates)} dates in transcript data have no matching video")
            print(f"Example unmatched transcript dates: {list(unmatched_transcript_dates)[:5]}")
        
        if unmatched_video_dates:
            print(f"Warning: {len(unmatched_video_dates)} dates in video data have no matching transcript")
            print(f"Example unmatched video dates: {list(unmatched_video_dates)[:5]}")
            
    except Exception as e:
        print(f"Error merging CSVs: {str(e)}")

if __name__ == "__main__":
    # Define paths in main function
    transcript_csv_path = "scraping-parliaments-internally/serbia/serbia_transcript_links.csv"
    video_csv_path = "scraping-parliaments-internally/serbia/serbia_video_links.csv"
    output_csv_path = "scraping-parliaments-internally/serbia/serbia_urls.csv"
    
    merge_csvs(transcript_csv_path, video_csv_path, output_csv_path)
