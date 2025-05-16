import csv
import re
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse, parse_qs

def extract_transcript_id(url: str) -> str:
    """Extract transcript ID from transcript URL."""
    # Try old format (e.g., '110617' from '.../2010-2011/110617/')
    match = re.search(r'/(\d{6})/?$', url)
    if match:
        return match.group(1)
    
    # Try new format with refs- prefix (e.g., '201617-10-01' from '.../2016-2017/refs-201617-10-01/')
    match = re.search(r'/refs-(\d{6}-\d{2}-\d{2})/?$', url)
    if match:
        return match.group(1)
    
    return None

def normalize_url(url: str) -> str:
    """Normalize URL to handle both old and new formats."""
    # Convert new format (refs-YYXXXX-MM-DD) to old format (YYMMDD)
    match = re.search(r'/refs-(\d{2})(?:\d{4})-(\d{2})-(\d{2})/?$', url)
    if match:
        year, month, day = match.groups()
        return re.sub(r'/refs-\d{6}-\d{2}-\d{2}/?$', f'/{year}{month}{day}/', url)
    return url

def load_transcripts(csv_path: str) -> Dict[str, dict]:
    """Load transcript information into a dictionary keyed by URL."""
    transcripts = {}
    transcript_ids = set()
    missing_ids = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transcript_id = extract_transcript_id(row['link'])
            if transcript_id:
                transcript_ids.add(transcript_id)
            else:
                missing_ids.append((row['date'], row['link']))
            transcripts[normalize_url(row['link'])] = {
                'date': row['date'],
                'transcript_url': row['link'],
                'transcript_id': transcript_id
            }
    print(f"Loaded {len(transcripts)} transcripts")
    print(f"Found {len(transcript_ids)} unique transcript IDs")
    if missing_ids:
        print("\nTranscripts without IDs:")
        for date, url in missing_ids:
            print(f"  Date: {date}")
            print(f"  URL:  {url}")
            print()
    print("\nExample transcript IDs (first 5):")
    for tid in sorted(list(transcript_ids))[:5]:
        print(f"  {tid}")
    return transcripts

def extract_video_id(url: str) -> str:
    """Extract video ID from video URL using format: {meid}-{del}."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    meid = params.get('meid', [None])[0]
    del_num = params.get('del', [None])[0]
    
    if meid and del_num:
        return f"{meid}-{del_num}"
    return None

def load_videos(csv_path: str) -> Dict[str, List[dict]]:
    """Load video information into a dictionary keyed by source_page URL."""
    videos = {}
    total_videos = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_page = normalize_url(row['source_page'])
            video_id = extract_video_id(row['url'])
            if source_page not in videos:
                videos[source_page] = []
            videos[source_page].append({
                'video_url': row['url'],
                'video_id': video_id,
                'video_type': row['type'],
                'video_format': row['format']
            })
            total_videos += 1
    print(f"Loaded {total_videos} videos for {len(videos)} unique transcripts")
    return videos

def combine_links():
    # Load data
    transcript_path = 'transcript_links_with_dates.csv'
    video_path = 'output/video_links.csv'
    
    transcripts = load_transcripts(transcript_path)
    videos = load_videos(video_path)
    
    # Track unmatched items
    unmatched_transcripts = set(transcripts.keys())
    unmatched_videos = set(videos.keys())
    
    # Prepare output directory
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # Combine data and write to CSV
    output_path = output_dir / 'combined_links.csv'
    matched_count = 0
    rows_written = 0
    
    fieldnames = ['date', 'transcript_id', 'transcript_url', 'video_id', 'video_url', 'video_type', 'video_format']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # For each transcript
        for transcript_url, transcript_data in transcripts.items():
            # Get associated videos
            transcript_videos = videos.get(transcript_url, [])
            
            if transcript_videos:
                matched_count += 1
                unmatched_transcripts.remove(transcript_url)
                unmatched_videos.remove(transcript_url)
                # Write a row for each video
                for video in transcript_videos:
                    row = {
                        'date': transcript_data['date'],
                        'transcript_id': transcript_data['transcript_id'],
                        'transcript_url': transcript_data['transcript_url'],
                        'video_id': video['video_id'],
                        'video_url': video['video_url'],
                        'video_type': video['video_type'],
                        'video_format': video['video_format']
                    }
                    writer.writerow(row)
                    rows_written += 1
    
    print(f"\nMatching Statistics:")
    print(f"Successfully matched {matched_count} transcripts with videos")
    print(f"Total rows written: {rows_written}")
    print(f"\nUnmatched Items:")
    print(f"{len(unmatched_transcripts)} transcripts have no matching videos")
    print(f"{len(unmatched_videos)} video source pages have no matching transcripts")
    
    # Print some examples of unmatched items
    print("\nExample unmatched transcripts (first 5):")
    for url in list(unmatched_transcripts)[:5]:
        print(f"  {url}")
    
    print("\nExample unmatched video source pages (first 5):")
    for url in list(unmatched_videos)[:5]:
        print(f"  {url}")

if __name__ == "__main__":
    combine_links() 