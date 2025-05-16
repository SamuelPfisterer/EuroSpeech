import os
import pandas as pd

# Define the directory containing the .srt files
subtitle_dir = "downloaded_subtitle"

# Initialize a list to store file information
file_info = []

def timestamp_to_seconds(timestamp):
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds"""
    try:
        hh_mm_ss, mmm = timestamp.split(',')
        hh, mm, ss = hh_mm_ss.split(':')
        return int(hh)*3600 + int(mm)*60 + int(ss) + int(mmm)/1000
    except Exception as e:
        print(f"Error converting timestamp {timestamp}: {e}")
        return None

def get_last_timestamp(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # Find the last timestamp in the file
            for line in reversed(lines):
                if '-->' in line:
                    # Extract the end timestamp
                    return line.split('-->')[1].strip()
        return None
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

# Iterate over all .srt files in the directory
for filename in os.listdir(subtitle_dir):
    if filename.endswith(".srt"):
        file_path = os.path.join(subtitle_dir, filename)
        
        print(f"Processing {file_path}")
        # Get the last timestamp
        last_timestamp = get_last_timestamp(file_path)
        
        # Append the file information to the list
        if last_timestamp is not None:
            # Convert to seconds
            duration_seconds = timestamp_to_seconds(last_timestamp)
            if duration_seconds is not None:
                print(f"Last timestamp: {last_timestamp} ({duration_seconds:.3f} seconds)")
                file_info.append({
                    "filename": filename,
                    "last_timestamp": last_timestamp,
                    "duration_seconds": duration_seconds
                })

# Convert the list to a DataFrame
df = pd.DataFrame(file_info)

# Ensure duration_seconds is numeric
df['duration_seconds'] = pd.to_numeric(df['duration_seconds'])

# Sort the DataFrame by duration_seconds in ascending order
df = df.sort_values(by="duration_seconds")

# Save the DataFrame to a CSV file
output_csv = "subtitle_timestamps.csv"
df.to_csv(output_csv, index=False)

print(f"CSV file saved to {output_csv}") 