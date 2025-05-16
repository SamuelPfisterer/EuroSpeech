import pandas as pd
from collections import Counter
import numpy as np

# Read both CSV files
transcripts_df = pd.read_csv('transcript_links.csv')
videos_df = pd.read_csv('video_links.csv')

# Convert date columns to datetime
transcripts_df['Date'] = pd.to_datetime(transcripts_df['Date'])
videos_df['Date'] = pd.to_datetime(videos_df['Date'])

# Pre-2020 analysis
transcripts_before_2020 = transcripts_df[transcripts_df['Date'] < '2020-01-01']
videos_before_2020 = videos_df[videos_df['Date'] < '2020-01-01']

# Get counts for each date before 2020
transcript_date_counts = Counter(transcripts_before_2020['Date'])
video_date_counts = Counter(videos_before_2020['Date'])

# Find dates with exactly one transcript
single_transcript_dates = {date for date, count in transcript_date_counts.items() if count == 1}

# Count videos on these dates
videos_with_single_transcript = sum(video_date_counts[date] for date in single_transcript_dates)

print("\nPre-2020 Statistics:")
print(f"Total videos before 2020: {len(videos_before_2020)}")
print(f"Videos on dates with exactly one transcript: {videos_with_single_transcript}")

# Post-2020 analysis
videos_post_2020 = videos_df[videos_df['Date'] >= '2020-01-01']
print(f"\nPost-2020 Statistics:")
print(f"Total videos from 2020 onwards: {len(videos_post_2020)}")

# Total potential matches
print(f"\nPotential Coverage:")
print(f"Videos that could be matched:")
print(f"- Pre-2020 videos with single transcript dates: {videos_with_single_transcript}")
print(f"- Post-2020 videos (to be matched via webpage): {len(videos_post_2020)}")
print(f"- Total potential matches: {videos_with_single_transcript + len(videos_post_2020)}")
print(f"- Percentage of all videos: {((videos_with_single_transcript + len(videos_post_2020)) / len(videos_df)) * 100:.2f}%")

# Detailed breakdown of pre-2020 single transcript cases
print("\nDetailed breakdown of pre-2020 cases with single transcript:")
single_transcript_video_counts = Counter(video_date_counts[date] for date in single_transcript_dates)
for video_count, date_count in sorted(single_transcript_video_counts.items()):
    total_videos = video_count * date_count
    print(f"- {date_count} dates with 1 transcript and {video_count} video(s): {total_videos} videos total") 