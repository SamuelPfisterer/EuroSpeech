import pandas as pd
import re
import os
from pathlib import Path

def extract_video_id(m3u8_url):
    """Extract a unique video_id from the m3u8 URL."""
    # Extract the format: 20241122091525-8880
    pattern = r'HLSArchive/([0-9]+-[0-9]+)/HLS'
    match = re.search(pattern, m3u8_url)
    if match:
        return match.group(1)
    return None

def main():
    # Load the CSVs
    extracted_links_df = pd.read_csv('extracted_m3u8_links.csv')
    ready_to_download_df = pd.read_csv('/itet-stor/spfisterer/net_scratch/Downloading/countries/croatia/links/media_links/croatian_parliament_media_links_ready_to_download.csv')
    
    print(f"Columns in extracted_links_df: {extracted_links_df.columns.tolist()}")
    print(f"Columns in ready_to_download_df: {ready_to_download_df.columns.tolist()}")
    
    # Extract video_id from m3u8_url
    extracted_links_df['video_id'] = extracted_links_df['m3u8_url'].apply(extract_video_id)
    
    # Create a mapping from m3u8_url to video_id
    unique_m3u8_urls = extracted_links_df.drop_duplicates('m3u8_url')
    
    # Count unique m3u8_urls and video_ids
    num_unique_m3u8_urls = len(unique_m3u8_urls)
    num_unique_video_ids = len(unique_m3u8_urls['video_id'].dropna().unique())
    
    print(f"Number of unique m3u8_urls: {num_unique_m3u8_urls}")
    print(f"Number of unique video_ids: {num_unique_video_ids}")
    
    # If fewer unique video_ids than m3u8_urls, we have duplicates
    if num_unique_video_ids < num_unique_m3u8_urls:
        print(f"Found {num_unique_m3u8_urls - num_unique_video_ids} duplicate video_ids")
        
        # Create a DataFrame to see which video_ids map to multiple m3u8_urls
        video_id_counts = unique_m3u8_urls.dropna(subset=['video_id']).groupby('video_id')['m3u8_url'].count()
        duplicate_video_ids = video_id_counts[video_id_counts > 1]
        
        print(f"Number of video_ids that map to multiple m3u8_urls: {len(duplicate_video_ids)}")
        if len(duplicate_video_ids) > 0:
            print("Sample of duplicate mappings:")
            for vid_id in duplicate_video_ids.index[:3]:  # Take first 3 examples
                urls = unique_m3u8_urls[unique_m3u8_urls['video_id'] == vid_id]['m3u8_url'].tolist()
                print(f"Video ID: {vid_id} maps to {len(urls)} m3u8_urls:")
                for url in urls[:2]:  # Show only first 2 URLs
                    print(f"  - {url}")
                if len(urls) > 2:
                    print(f"  - ... and {len(urls)-2} more")
    
    # Save the updated dataframe
    extracted_links_df.to_csv('extracted_m3u8_links_with_video_ids.csv', index=False)
    print("Saved extracted_m3u8_links_with_video_ids.csv")
    
    # Now create mapping from original_url to video_id
    url_to_video_id = dict(zip(extracted_links_df['original_url'], extracted_links_df['video_id']))
    
    # Map to ready_to_download_df
    ready_to_download_df['video_id'] = ready_to_download_df['generic_m3u8_link'].map(lambda x: url_to_video_id.get(x))
    
    # Report matching results
    matched_count = ready_to_download_df['video_id'].notna().sum()
    print(f"Matched {matched_count} out of {len(ready_to_download_df)} rows in ready_to_download_df")
    
    # Save the final dataframe
    ready_to_download_df.to_csv('croatian_parliament_media_links_final.csv', index=False)
    print("Saved croatian_parliament_media_links_final.csv")

if __name__ == "__main__":
    main()