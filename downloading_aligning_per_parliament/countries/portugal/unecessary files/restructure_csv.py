import pandas as pd

# Read the original CSV
df = pd.read_csv('all_session_recordings.csv')

# Create new columns by duplicating the link_to_session column
df['generic_video_link'] = df['link_to_session']
df['processed_transcript_text_link'] = df['link_to_session']

# Drop the original link_to_session column
df = df.drop('link_to_session', axis=1)

# Save the restructured CSV
df.to_csv('all_session_recordings_restructured.csv', index=False)

print("CSV file has been restructured successfully!") 