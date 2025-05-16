import csv
import pandas as pd
import re
from typing import Callable

def merge_csvs_slovenia(
    transcript_csv_path: str,
    video_csv_path: str,
    output_csv_path: str
) -> None:
    """
    Merge Slovenia transcript and video CSVs based on date extracted from IDs.

    Args:
        transcript_csv_path: Path to the transcript CSV file.
        video_csv_path: Path to the video CSV file.
        output_csv_path: Path to save the merged CSV file.
    """
    try:
        # Load transcript data
        transcript_df = pd.read_csv(transcript_csv_path)
        transcript_df["date"] = transcript_df["transcript_id"].apply(extract_date_from_id)

        # Load video data
        video_df = pd.read_csv(video_csv_path)
        video_df["date"] = video_df["video_id"].apply(extract_date_from_id)

        # Rename title columns to avoid automatic suffixes
        transcript_df = transcript_df.rename(columns={"title": "transcript_title"})
        video_df = video_df.rename(columns={"title": "video_title"})

        # Merge DataFrames
        merged_df = pd.merge(
            transcript_df,
            video_df,
            on="date",
            how="inner",
        )

        # Create merged ID
        merged_df["merged_id"] = merged_df["transcript_id"] + "_" + merged_df["video_id"]

        # Save merged DataFrame to CSV
        merged_df.to_csv(output_csv_path, index=False)
        print(f"Merged data saved to {output_csv_path}")

        # Report unmatched keys
        transcript_dates = set(transcript_df["date"])
        video_dates = set(video_df["date"])

        unmatched_transcript_dates = transcript_dates - video_dates
        unmatched_video_dates = video_dates - transcript_dates

        if unmatched_transcript_dates:
            print(
                f"Warning: {len(unmatched_transcript_dates)} dates in transcript data have no matching video"
            )
            print(
                f"Example unmatched transcript dates: {list(unmatched_transcript_dates)[:5]}"
            )

        if unmatched_video_dates:
            print(
                f"Warning: {len(unmatched_video_dates)} dates in video data have no matching transcript"
            )
            print(f"Example unmatched video dates: {list(unmatched_video_dates)[:5]}")

    except Exception as e:
        print(f"Error merging CSVs: {str(e)}")

def extract_date_from_id(id_str: str) -> str:
    """
    Extract date from Slovenia ID format.
    Example: "slovenia_123_session_0_2022-05-20" -> "2022-05-20"
    
    Args:
        id_str: ID string containing a date
        
    Returns:
        Extracted date string
    """
    # Match the date pattern at the end of the ID: YYYY-MM-DD
    return id_str.split('_')[-1]

if __name__ == "__main__":
    # Define paths
    transcript_csv_path = "scraping-parliaments-internally/slovenia/transcript_links.csv"
    video_csv_path = "scraping-parliaments-internally/slovenia/video_links.csv"
    output_csv_path = "scraping-parliaments-internally/slovenia/slovenia_urls.csv"
    
    # Merge CSVs
    merge_csvs_slovenia(
        transcript_csv_path,
        video_csv_path,
        output_csv_path
    )
