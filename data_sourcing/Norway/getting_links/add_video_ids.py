import csv
from urllib.parse import urlparse, parse_qs
from pathlib import Path

def extract_video_id(url: str, video_type: str) -> str:
    """Extract video ID from video URL using format: {meid}-{del}."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    meid = params.get('meid', [None])[0]
    del_num = params.get('del', [''])[0]
    
    # Try to get part number from video_type if it contains "del X"
    if "del" in video_type.lower():
        try:
            del_num = video_type.lower().split("del")[1].strip()
        except:
            pass
    
    # If del_num is empty but we have meid, default to "1"
    if meid and not del_num:
        del_num = "1"
    
    if meid and del_num:
        return f"{meid}-{del_num}"
    return None

def add_video_ids(input_path: str, output_path: str):
    """Add video IDs to the combined links CSV file."""
    # Read all rows
    video_ids = {}  # Track video IDs and their first occurrence {video_id: row}
    skipped_rows = []  # Track skipped rows for reporting
    rows_without_ids = []  # Track rows that don't get a video ID
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Get existing fieldnames and add video_id if not present
        fieldnames = list(reader.fieldnames)
        if 'video_id' not in fieldnames:
            # Insert video_id before video_url
            insert_pos = fieldnames.index('video_url')
            fieldnames.insert(insert_pos, 'video_id')
        
        for row in reader:
            # Create a new row with all existing fields
            new_row = {}
            for field in fieldnames:
                if field == 'video_id':
                    video_id = extract_video_id(row['video_url'], row['video_type'])
                    new_row[field] = video_id
                else:
                    new_row[field] = row.get(field, '')
            
            # Skip English versions
            if "english" in row['date'].lower() or "eng" in row['transcript_url'].lower():
                skipped_rows.append(("English version", new_row))
                continue
            
            # Track rows without video IDs
            if not video_id:
                rows_without_ids.append(new_row)
                continue
            
            # Handle duplicates by keeping first occurrence
            if video_id in video_ids:
                skipped_rows.append(("Duplicate video", new_row))
                continue
            video_ids[video_id] = new_row
    
    # Only keep rows with unique video IDs
    rows = list(video_ids.values())
    
    # Write updated rows
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Total input rows: {sum([len(rows), len(skipped_rows), len(rows_without_ids)])}")
    print(f"Written rows with unique video IDs: {len(rows)}")
    print(f"Found {len(video_ids)} unique video IDs")
    print(f"Skipped {len(skipped_rows)} duplicate/English rows")
    print(f"Found {len(rows_without_ids)} rows without video IDs")
    
    if rows_without_ids:
        print("\nRows without video IDs:")
        for row in rows_without_ids[:5]:  # Show first 5 examples
            print(f"\nDate: {row['date']}")
            print(f"Video Type: {row['video_type']}")
            print(f"Video URL: {row['video_url']}")
    
    if skipped_rows:
        print("\nSkipped rows:")
        for reason, row in skipped_rows:
            print(f"\nReason: {reason}")
            print(f"Date: {row['date']}")
            print(f"Video ID: {row['video_id']}")
            print(f"Video Type: {row['video_type']}")
            print(f"Video URL: {row['video_url']}")
    
    print("\nFirst few rows with video IDs:")
    for row in rows[:3]:
        print(f"\nDate: {row['date']}")
        print(f"Transcript ID: {row['transcript_id']}")
        print(f"Video ID: {row['video_id']}")
        print(f"Video URL: {row['video_url']}")

if __name__ == "__main__":
    input_file = "output/combined_links.csv"
    output_file = "output/combined_links_with_ids.csv"
    add_video_ids(input_file, output_file) 