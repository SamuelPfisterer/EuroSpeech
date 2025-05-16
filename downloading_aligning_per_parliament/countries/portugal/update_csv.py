import pandas as pd

# Read the CSV file
df = pd.read_csv('links/portugal_links.csv')

# Create video_id from cycle, legislation, and session_number
df['video_id'] = df.apply(lambda row: f"{row['cycle']}_{row['legislation']}_{row['session_number']}", axis=1)

# Check for duplicate IDs
duplicates = df['video_id'].duplicated()
if duplicates.any():
    print("WARNING: Found duplicate video_ids:")
    print(df[duplicates]['video_id'].tolist())
    raise ValueError("Duplicate video_ids found! Please check the data.")

# Reorder columns to put video_id first
cols = ['video_id'] + [col for col in df.columns if col != 'video_id']
df = df[cols]

# Save the updated CSV
df.to_csv('links/portugal_links.csv', index=False)

print("Added video_id column to CSV file. No duplicates found.") 