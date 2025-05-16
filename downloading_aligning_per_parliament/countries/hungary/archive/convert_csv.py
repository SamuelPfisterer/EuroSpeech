import pandas as pd
import os

# Read the original CSV
input_file = 'hungary_parliament_sessions.csv'
output_file = 'hungary_parliament_sessions_converted.csv'

# Read the CSV
df = pd.read_csv(input_file)

# Function to extract cycle number from transcript link
def extract_cycle(url):
    try:
        # The cycle is after 'p_ckl=' in the URL
        cycle = url.split('p_ckl%3D')[1].split('%')[0]
        return cycle
    except:
        return '42'  # Default to 42 if extraction fails

# Rename columns
df = df.rename(columns={
    'session_link': 'transcript_link',
    'video_link': 'generic_m3u8_link'
})

# Extract cycle numbers and create transcript_ids
df['cycle'] = df['transcript_link'].apply(extract_cycle)
df['transcript_id'] = df.apply(lambda row: f'cycle_{row["cycle"]}_session_{row["session_number"]}', axis=1)

# Check for uniqueness of transcript_ids
duplicate_ids = df[df['transcript_id'].duplicated()]['transcript_id'].tolist()
if duplicate_ids:
    print("WARNING: Found duplicate transcript_ids:")
    for id in duplicate_ids:
        print(f"- {id}")
        # Show the rows with this duplicate id
        print(df[df['transcript_id'] == id][['transcript_id', 'date', 'session_number', 'cycle']])
else:
    print("All transcript_ids are unique!")

# Reorder columns to match required format
column_order = [
    'transcript_id',
    'date',
    'session_number',
    'transcript_link',
    'generic_m3u8_link',
    'nature_of_sitting',
    'day'
]
df = df[column_order]

# Save the modified CSV
df.to_csv(output_file, index=False)
print(f"Converted CSV saved to: {output_file}")

# Optionally, replace the original file
# os.rename(output_file, input_file)
# print("Original file replaced with converted version") 