import csv
import pandas as pd
import re
from typing import Callable
from functools import partial

def extract_keys(df: pd.DataFrame, id_name: str, location_name: str) -> pd.Series:
    def build_key(row):
        # Extract the last part after splitting the id_name by "_"
        date_part = str(row[id_name]).split("_")[-1]
        # Check the location and append the appropriate suffix
        if "Commons" in row[location_name]:
            suffix = "_Commons"
        else:
            suffix = "_Westminster"
        return date_part + suffix

    return df.apply(build_key, axis=1)

def merge_csvs_generic(
    transcript_csv_path: str,
    video_csv_path: str,
    output_csv_path: str,
    pre_process_transcript_key,
    pre_process_video_key,
) -> None:
    """
    Merge transcript and video CSVs based on a generic join key.

    Args:
        transcript_csv_path: Path to the transcript CSV file.
        video_csv_path: Path to the video CSV file.
        output_csv_path: Path to save the merged CSV file.
        pre_process_transcript_key: Optional function to pre-process the join key in the transcript data.
        pre_process_video_key: Optional function to pre-process the join key in the video data.
    """
    try:
        transcript_df = pd.read_csv(transcript_csv_path)
        transcript_df["key"] = pre_process_transcript_key(transcript_df)       # Load transcript data
 

        # Load video data
        video_df = pd.read_csv(video_csv_path)
        video_df["key"] = pre_process_video_key(video_df)

        # Merge DataFrames
        merged_df = pd.merge(
            transcript_df,
            video_df,
            left_on="key",
            right_on="key",
            how="inner",
        )

        # Save merged DataFrame to CSV
        merged_df.to_csv(output_csv_path, index=False)
        print(f"Merged data saved to {output_csv_path}")

        # Report unmatched keys
        transcript_keys = set(transcript_df["key"])
        video_keys = set(video_df["key"])

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
    transcript_csv_path = "scraping-parliaments-internally/uk/transcript_links_parallel.csv"
    video_csv_path = "scraping-parliaments-internally/uk/video_links.csv"
    output_csv_path = "scraping-parliaments-internally/uk/uk_urls_2012-2025.csv"

    # Merge CSVs using the date extraction function
    merge_csvs_generic(
        transcript_csv_path,
        video_csv_path,
        output_csv_path,
        pre_process_transcript_key=partial(extract_keys, id_name="transcript_id", location_name="location"),
        pre_process_video_key=partial(extract_keys, id_name="video_id", location_name="location"),
    )