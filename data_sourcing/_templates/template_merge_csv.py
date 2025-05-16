import csv
import pandas as pd
import re
from typing import Callable

def merge_csvs_generic(
    transcript_csv_path: str,
    video_csv_path: str,
    output_csv_path: str,
    join_key_transcript: str,
    join_key_video: str,
    pre_process_transcript_key: Callable[[str], str] = None,
    pre_process_video_key: Callable[[str], str] = None,
) -> None:
    """
    Merge transcript and video CSVs based on a generic join key.

    Args:
        transcript_csv_path: Path to the transcript CSV file.
        video_csv_path: Path to the video CSV file.
        output_csv_path: Path to save the merged CSV file.
        join_key_transcript: The column name in the transcript CSV to use for joining.
        join_key_video: The column name in the video CSV to use for joining.
        pre_process_transcript_key: Optional function to pre-process the join key in the transcript data.
        pre_process_video_key: Optional function to pre-process the join key in the video data.
    """
    try:
        # Load transcript data
        transcript_df = pd.read_csv(transcript_csv_path)
        transcript_df["date"] = transcript_df["transcript_id"].apply(pre_process_transcript_key)

        # Load video data
        video_df = pd.read_csv(video_csv_path)
        video_df["date"] = video_df["video_id"].apply(pre_process_video_key)

        # Rename title columns to avoid automatic suffixes
        transcript_df = transcript_df.rename(columns={"title": "transcript_title"})
        video_df = video_df.rename(columns={"title": "video_title"})

        # Merge DataFrames
        merged_df = pd.merge(
            transcript_df,
            video_df,
            left_on=join_key_transcript,
            right_on=join_key_video,
            how="inner",
        )

        # Create merged ID if needed
        if 'transcript_id' in merged_df.columns and 'video_id' in merged_df.columns:
            merged_df["merged_id"] = merged_df["transcript_id"] + "_" + merged_df["video_id"]

        # Save merged DataFrame to CSV
        merged_df.to_csv(output_csv_path, index=False)
        print(f"Merged data saved to {output_csv_path}")

        # Report unmatched keys
        transcript_keys = set(transcript_df[join_key_transcript])
        video_keys = set(video_df[join_key_video])

        unmatched_transcript_keys = transcript_keys - video_keys
        unmatched_video_keys = video_keys - transcript_keys

        if unmatched_transcript_keys:
            print(
                f"Warning: {len(unmatched_transcript_keys)} keys in transcript data have no matching video"
            )
            print(
                f"Example unmatched transcript keys: {list(unmatched_transcript_keys)[:5]}"
            )

        if unmatched_video_keys:
            print(
                f"Warning: {len(unmatched_video_keys)} keys in video data have no matching transcript"
            )
            print(f"Example unmatched video keys: {list(unmatched_video_keys)[:5]}")

    except Exception as e:
        print(f"Error merging CSVs: {str(e)}")

if __name__ == "__main__":
    # Define paths and join keys
    transcript_csv_path = "scraping-parliaments-internally/serbia/serbia_transcript_links.csv"
    video_csv_path = "scraping-parliaments-internally/serbia/serbia_video_links.csv"
    output_csv_path = "scraping-parliaments-internally/serbia/serbia_urls.csv"
    join_key_transcript = "date"
    join_key_video = "date"

    def extract_date_from_id(id_str: str) -> str:
        return id_str.split('_')[-1]

    # Merge CSVs using the date extraction function
    merge_csvs_generic(
        transcript_csv_path,
        video_csv_path,
        output_csv_path,
        join_key_transcript,
        join_key_video,
        pre_process_transcript_key=extract_date_from_id,
        pre_process_video_key=extract_date_from_id,
    )