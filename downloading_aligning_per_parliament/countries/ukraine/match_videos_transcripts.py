import os
import pandas as pd
import re
from pathlib import Path

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
transcripts_dirs = [os.path.join(current_dir, 'downloaded_transcript', 'ukraine_IX_convocation'),
                    os.path.join(current_dir, 'downloaded_transcript', 'ukraine_VIII_convocation')]
ukraine_links_path = os.path.join(current_dir, 'links', 'ukraine_links.csv')
ukraine_links_original_path = os.path.join(current_dir, 'links', 'ukraine_links_original.csv')
output_path = os.path.join(current_dir, 'links', 'ukraine_links_final.csv')

# Load video links data
ukraine_links_df = pd.read_csv(ukraine_links_path)

# Get list of transcript files
transcript_files = []
for transcripts_dir in transcripts_dirs:
    if os.path.exists(transcripts_dir):
        transcript_files.extend([f for f in os.listdir(transcripts_dir) if f.endswith('.htm')])
    else:
        print(f"Transcript directory not found: {transcripts_dir}")

# Extract dates from transcript filenames
transcript_dates = {}
for filename in transcript_files:
    # Extract date part (YYYYMMDD) from filename
    match = re.match(r'(\d{8})(?:-\d+)?\.htm', filename)
    if match:
        date_str = match.group(1)
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Store the filename without extension as transcript_id
        transcript_id = os.path.splitext(filename)[0]
        
        if formatted_date not in transcript_dates:
            transcript_dates[formatted_date] = []
        transcript_dates[formatted_date].append(transcript_id)

# Create the final dataframe with matches
final_rows = []

# Process each row in ukraine_links.csv
for _, row in ukraine_links_df.iterrows():
    # Get the date from the row (assuming the date column exists)
    if 'date' in row:
        date = row['date']
    elif 'Date' in row:
        date = row['Date']
    else:
        # Try to find any column that might contain a date in the format YYYY-MM-DD
        date = None
        for col, val in row.items():
            if isinstance(val, str) and re.match(r'\d{4}-\d{2}-\d{2}', val):
                date = val
                break
        
        if date is None:
            print(f"No date column found for row: {row}")
            continue
    
    # Find matching transcript files for this date
    if date in transcript_dates:
        for transcript_id in transcript_dates[date]:
            # Create a new row with the transcript_id and all original columns
            new_row = row.to_dict()
            new_row['transcript_id'] = transcript_id
            final_rows.append(new_row)
    else:
        # No matching transcripts found
        print(f"No matching transcript found for date: {date}")

# Create final dataframe
if final_rows:
    final_df = pd.DataFrame(final_rows)
    
    # Reorder columns to have transcript_id first
    cols = ['transcript_id'] + [col for col in final_df.columns if col != 'transcript_id']
    final_df = final_df[cols]
    
    # Save to CSV
    final_df.to_csv(output_path, index=False)
    print(f"Created {output_path} with {len(final_df)} rows")
else:
    print("No matches found between videos and transcripts")
