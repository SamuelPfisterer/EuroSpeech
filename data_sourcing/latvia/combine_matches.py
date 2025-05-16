import pandas as pd
import json
from datetime import datetime
from collections import defaultdict
import os
import re

def load_data():
    """
    Load data from all source files.
    """
    # Load all data sources
    try:
        post_2020_matches = pd.read_csv('post_2020_matches.csv')
        print(f"Loaded {len(post_2020_matches)} post-2020 matches")
    except FileNotFoundError:
        print("Warning: post_2020_matches.csv not found. Proceeding without post-2020 matches.")
        post_2020_matches = pd.DataFrame(columns=['video_url', 'transcript_url', 'transcript_date', 'video_time'])
    
    transcripts_df = pd.read_csv('transcript_links.csv')
    videos_df = pd.read_csv('video_links.csv')
    
    # Convert date columns to datetime
    transcripts_df['Date'] = pd.to_datetime(transcripts_df['Date'])
    videos_df['Date'] = pd.to_datetime(videos_df['Date'])
    
    if 'transcript_date' in post_2020_matches.columns:
        post_2020_matches['transcript_date'] = pd.to_datetime(post_2020_matches['transcript_date'])
    
    return post_2020_matches, transcripts_df, videos_df

def create_combined_matches(post_2020_matches, transcripts_df, videos_df):
    """
    Create a combined dataset with all matches.
    """
    # Create a dictionary to store all matches
    # Key: video URL, Value: list of transcript URLs and metadata
    all_matches = defaultdict(list)
    
    # Create a set of valid video URLs for quick lookup
    valid_video_urls = set(videos_df['URL'].unique())
    
    # First, add all post-2020 matches (from webpage scraping)
    if not post_2020_matches.empty:
        for _, row in post_2020_matches.iterrows():
            video_url = row['video_url']
            transcript_url = row['transcript_url']
            
            # Skip if video URL is not in our videos_df
            if video_url not in valid_video_urls:
                continue
                
            # Check if this video already has this transcript
            if not any(t.get('transcript_url') == transcript_url for t in all_matches[video_url]):
                all_matches[video_url].append({
                    'transcript_url': transcript_url,
                    'match_type': 'webpage',
                    'video_time': row.get('video_time', '')
                })
    
    # Get all videos that don't have matches yet
    matched_videos = set(all_matches.keys())
    unmatched_videos = videos_df[~videos_df['URL'].isin(matched_videos)]
    
    # For pre-2020 videos, match by date
    pre_2020_videos = unmatched_videos[unmatched_videos['Date'] < '2020-01-01']
    
    # Find dates with exactly one transcript (for reliable matching)
    transcript_date_counts = transcripts_df['Date'].value_counts()
    single_transcript_dates = transcript_date_counts[transcript_date_counts == 1].index
    
    # Match pre-2020 videos with single transcript dates
    for _, video_row in pre_2020_videos.iterrows():
        video_date = video_row['Date']
        video_url = video_row['URL']
        
        # If this date has exactly one transcript, it's a reliable match
        if video_date in single_transcript_dates:
            transcript_row = transcripts_df[transcripts_df['Date'] == video_date].iloc[0]
            transcript_url = transcript_row['URL']
            
            all_matches[video_url].append({
                'transcript_url': transcript_url,
                'match_type': 'date_single',
                'video_time': video_row.get('Time', '')
            })
        else:
            # For dates with multiple transcripts, add all as potential matches
            matching_transcripts = transcripts_df[transcripts_df['Date'] == video_date]
            
            for _, transcript_row in matching_transcripts.iterrows():
                transcript_url = transcript_row['URL']
                
                all_matches[video_url].append({
                    'transcript_url': transcript_url,
                    'match_type': 'date_multiple',
                    'video_time': video_row.get('Time', '')
                })
    
    # For remaining post-2020 videos, also try date-based matching
    post_2020_videos = unmatched_videos[unmatched_videos['Date'] >= '2020-01-01']
    
    for _, video_row in post_2020_videos.iterrows():
        video_date = video_row['Date']
        video_url = video_row['URL']
        
        # Match with all transcripts from the same date
        matching_transcripts = transcripts_df[transcripts_df['Date'] == video_date]
        
        for _, transcript_row in matching_transcripts.iterrows():
            transcript_url = transcript_row['URL']
            
            all_matches[video_url].append({
                'transcript_url': transcript_url,
                'match_type': 'date_post_2020',
                'video_time': video_row.get('Time', '')
            })
    
    return all_matches

def create_main_py_compatible_output(all_matches, videos_df):
    """
    Create a CSV output compatible with main.py format.
    Each row contains a video and its corresponding transcript.
    """
    # Create a list to store the rows for our output
    output_rows = []
    
    # Process each video and its matches
    for video_url, transcript_matches in all_matches.items():
        # Get video metadata - with error handling
        video_rows = videos_df[videos_df['URL'] == video_url]
        
        if video_rows.empty:
            print(f"Warning: Video URL not found in videos_df: {video_url}")
            continue
            
        video_row = video_rows.iloc[0]
        
        # Extract video ID from URL
        video_id = os.path.basename(video_url).split('_')[0]
        
        # For each transcript match, create a separate row
        for match in transcript_matches:
            transcript_url = match['transcript_url']
            match_type = match['match_type']
            
            # Extract transcript ID from URL
            # Assumes the transcript ID is the last part of the URL after 'view/'
            transcript_id_match = re.search(r'/view/(\d+)', transcript_url)
            transcript_id = transcript_id_match.group(1) if transcript_id_match else 'unknown'
            
            # Create a row for this video-transcript pair
            output_row = {
                'video_id': video_id,
                'transcript_id': transcript_id,
                'mp4_video_link': video_url,  # Direct link to video
                'html_link': transcript_url,  # Direct link to transcript
                'match_type': match_type,     # Additional metadata
                'video_date': video_row['Date'].strftime('%Y-%m-%d'),
                'video_time': video_row['Time'],
                'video_legislation': video_row['Legislation']
            }
            
            # Add title if available
            if 'Title' in video_row and pd.notna(video_row['Title']) and video_row['Title'] != '':
                output_row['video_title'] = video_row['Title']
            
            output_rows.append(output_row)
    
    # Convert to DataFrame
    output_df = pd.DataFrame(output_rows)
    
    # Reorder columns to match main.py expectations
    columns_order = ['video_id', 'transcript_id', 'mp4_video_link', 'html_link']
    # Add any remaining columns
    for col in output_df.columns:
        if col not in columns_order:
            columns_order.append(col)
    
    output_df = output_df[columns_order]
    
    return output_df

def main():
    # Load all data
    post_2020_matches, transcripts_df, videos_df = load_data()
    
    print(f"Loaded {len(transcripts_df)} transcripts and {len(videos_df)} videos")
    
    # Create combined matches
    all_matches = create_combined_matches(post_2020_matches, transcripts_df, videos_df)
    
    # Create main.py compatible output
    output_df = create_main_py_compatible_output(all_matches, videos_df)
    
    # Save to CSV
    csv_output = 'latvia_parliament_meetings.csv'
    output_df.to_csv(csv_output, index=False)
    print(f"Saved {len(output_df)} video-transcript pairs to {csv_output}")
    
    # Print statistics
    print("\nMatching Statistics:")
    print(f"Total videos: {len(videos_df)}")
    print(f"Videos with at least one transcript match: {len(all_matches)}")
    print(f"Total video-transcript pairs: {len(output_df)}")
    print(f"Coverage: {len(all_matches)/len(videos_df)*100:.2f}%")
    
    # Count by match type
    match_types = output_df['match_type'].value_counts()
    print("\nMatch types:")
    for match_type, count in match_types.items():
        print(f"  {match_type}: {count} pairs")
    
    # Count transcripts per video
    transcripts_per_video = output_df.groupby('video_id').size()
    avg_transcripts = transcripts_per_video.mean()
    print(f"\nAverage transcripts per video: {avg_transcripts:.2f}")
    
    # Distribution of transcripts per video
    transcript_counts = transcripts_per_video.value_counts().sort_index()
    print("\nNumber of transcripts per video:")
    for count, num_videos in transcript_counts.items():
        print(f"  {count} transcript(s): {num_videos} videos")

if __name__ == "__main__":
    main() 